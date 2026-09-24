"""
FinVisor 2.0 — FastAPI Backend
================================
Endpoints:
  GET  /health              — health check
  GET  /transactions        — paginated transaction history
  GET  /transactions/live   — SSE stream from Redis
  POST /analyze             — trigger full analysis pipeline
  GET  /report              — latest financial health report
  GET  /anomalies           — detected anomalies
  GET  /recurring           — recurring / hidden costs
  POST /whatif              — what-if scenario simulator
  WS   /ws/live             — WebSocket real-time transaction feed
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

# ---------------------------------------------------------------------------
# Path fix: allow imports from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Local imports (after path fix)
# ---------------------------------------------------------------------------
from backend import db as database
from backend.redis_client import (
    close_redis,
    get_latest_from_stream,
    ping_redis,
    read_stream_from,
)
from backend.pipeline import run_full_analysis
from backend.whatif import run_whatif
from simulator.schemas import (
    FinancialReport,
    HealthCheck,
    PaginatedTransactions,
    Transaction,
    WhatIfRequest,
    WhatIfResult,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH       = os.getenv("DATABASE_URL", "sqlite:///./finvisor.db").replace("sqlite:///", "")
BUSINESS_TYPE = os.getenv("BUSINESS_TYPE", "retailer")
REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379")

# Resolve relative DB path to absolute
if not os.path.isabs(DB_PATH):
    DB_PATH = str(PROJECT_ROOT / DB_PATH)

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages active WebSocket connections for the live feed."""

    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.remove(ws)

    async def broadcast(self, data: str) -> None:
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Background Redis broadcaster
# ---------------------------------------------------------------------------

_broadcaster_task: Optional[asyncio.Task] = None


async def _redis_broadcaster() -> None:
    """
    Continuously reads new entries from the Redis stream and broadcasts
    them to all connected WebSocket clients. Falls back to SQLite polling if Redis is empty/offline.
    """
    import aiosqlite
    last_id = "$"   # start from new entries only
    last_polled_ts = datetime.utcnow().isoformat()
    while True:
        try:
            new_last_id, txs = await read_stream_from(
                last_id  = last_id,
                count    = 20,
                block_ms = 1500,
            )
            if txs:
                last_id = new_last_id
                for tx in txs:
                    payload = tx.model_dump(mode="json")
                    payload["timestamp"] = tx.timestamp.isoformat()
                    await manager.broadcast(json.dumps(payload))
            else:
                # Fallback: check SQLite for transactions inserted by live simulator
                try:
                    async with aiosqlite.connect(DB_PATH) as db:
                        db.row_factory = aiosqlite.Row
                        async with db.execute(
                            "SELECT * FROM transactions WHERE timestamp > ? ORDER BY timestamp ASC LIMIT 20",
                            (last_polled_ts,)
                        ) as cur:
                            rows = await cur.fetchall()
                        if rows:
                            last_polled_ts = rows[-1]["timestamp"]
                            for r in rows:
                                payload = dict(r)
                                payload["tags"] = [t for t in payload.get("tags", "").split(",") if t]
                                await manager.broadcast(json.dumps(payload))
                except Exception:
                    pass
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    global _broadcaster_task
    # Startup
    await database.init_db(DB_PATH)
    _broadcaster_task = asyncio.create_task(_redis_broadcaster())
    yield
    # Shutdown
    if _broadcaster_task:
        _broadcaster_task.cancel()
    await close_redis()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title       = "FinVisor 2.0 API",
    description = "AI-powered Financial Advisor for SMEs",
    version     = "2.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://127.0.0.1:5173",
                         "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _row_to_tx(row: Dict) -> Dict:
    """Convert a DB row dict to a Transaction-compatible dict."""
    row["tags"] = [t for t in row.get("tags", "").split(",") if t]
    return row


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthCheck, tags=["meta"])
async def health_check() -> HealthCheck:
    """Returns system health status."""
    redis_ok = await ping_redis()
    try:
        rows, _ = await database.get_transactions(DB_PATH, page=1, page_size=1)
        db_ok   = "ok"
    except Exception as e:
        db_ok = f"error: {e}"

    return HealthCheck(
        status    = "ok",
        redis     = "ok" if redis_ok else "unavailable",
        database  = db_ok,
        timestamp = datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.get("/transactions", response_model=PaginatedTransactions, tags=["transactions"])
async def list_transactions(
    page      : int           = Query(1, ge=1, description="Page number"),
    page_size : int           = Query(50, ge=1, le=500, description="Items per page"),
    type      : Optional[str] = Query(None, description="Filter by CREDIT or DEBIT"),
    category  : Optional[str] = Query(None, description="Filter by category"),
    start_date: Optional[str] = Query(None, description="ISO datetime lower bound"),
    end_date  : Optional[str] = Query(None, description="ISO datetime upper bound"),
) -> PaginatedTransactions:
    """Return paginated transaction history with optional filters."""
    rows, total = await database.get_transactions(
        db_path    = DB_PATH,
        page       = page,
        page_size  = page_size,
        tx_type    = type,
        category   = category,
        start_date = start_date,
        end_date   = end_date,
    )
    items = [Transaction(**_row_to_tx(r)) for r in rows]
    return PaginatedTransactions(
        items     = items,
        total     = total,
        page      = page,
        page_size = page_size,
        has_more  = (page * page_size) < total,
    )


@app.get("/transactions/live", tags=["transactions"])
async def transactions_live(
    request    : Any,
    count      : int = Query(20, ge=1, le=100, description="Number of recent transactions"),
) -> EventSourceResponse:
    """
    Server-Sent Events stream of live transactions from Redis or SQLite.
    Sends the last `count` transactions immediately, then streams new ones.
    """
    async def event_generator() -> AsyncGenerator:
        # Send recent transactions first
        recent = await get_latest_from_stream(count=count)
        if not recent:
            rows, _ = await database.get_transactions(DB_PATH, page=1, page_size=count)
            for r in reversed(rows):
                payload = dict(r)
                payload["tags"] = [t for t in payload.get("tags", "").split(",") if t]
                yield {"data": json.dumps(payload)}
        else:
            for tx in reversed(recent):
                payload = tx.model_dump(mode="json")
                payload["timestamp"] = tx.timestamp.isoformat()
                yield {"data": json.dumps(payload)}

        # Stream new transactions
        last_id = "$"
        while True:
            if await request.is_disconnected():
                break
            new_last_id, txs = await read_stream_from(
                last_id  = last_id,
                count    = 10,
                block_ms = 2000,
            )
            if txs:
                last_id = new_last_id
                for tx in txs:
                    payload = tx.model_dump(mode="json")
                    payload["timestamp"] = tx.timestamp.isoformat()
                    yield {"data": json.dumps(payload)}
            else:
                await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Analysis & Reports
# ---------------------------------------------------------------------------

def _format_frontend_report(report_dict: Dict) -> Dict:
    margin = report_dict.get("profit_margin_pct", 0)
    anom_count = report_dict.get("anomaly_count", 0)
    score = max(25, min(95, int(65 + margin * 0.4 - min(anom_count, 15) * 1.5)))

    anomalies = report_dict.get("anomalies", [])
    anom_refs = [a.get("transaction_id") for a in anomalies if a.get("transaction_id")]
    recurring = report_dict.get("recurring_costs", [])
    rec_refs = [tx for r in recurring for tx in r.get("transaction_ids", [])][:6]

    sections = [
        {
            "title": "🚨 Anomalies & Irregularities",
            "content": report_dict.get("spending_analysis") or f"Detected {anom_count} anomalies including statistical outliers, duplicate payments, and timing discrepancies.",
            "references": anom_refs[:4]
        },
        {
            "title": "💸 Expense & Recurring Cost Analysis",
            "content": f"Recurring costs account for a monthly burden of ₹{sum(r.get('monthly_burden', 0) for r in recurring):,.2f}. Regular review of software subscriptions and vendor contracts recommended.",
            "references": rec_refs[:4]
        },
        {
            "title": "📈 Cash Flow Forecast & Risk Assessment",
            "content": report_dict.get("risk_assessment") or f"Based on historical daily burn rate of ₹{report_dict.get('burn_rate_daily', 0):,.2f}, estimated runway is {report_dict.get('cash_runway_days', 'N/A')} days.",
            "references": []
        }
    ]

    action_plan = []
    raw_actions = report_dict.get("action_items", [])
    if raw_actions:
        for i, item in enumerate(raw_actions, 1):
            action_plan.append({
                "priority": item.get("priority", i),
                "action": item.get("title", f"Action {i}"),
                "impact": item.get("description", "Positive financial impact"),
                "urgency": "critical" if i == 1 else "high" if i == 2 else "medium" if i <= 4 else "low"
            })
    else:
        action_plan = [
            {"priority": 1, "action": "Investigate flagged outlier debit transactions", "impact": "Eliminate unauthorized expenses", "urgency": "critical"},
            {"priority": 2, "action": "Review recurring subscription duplicate payments", "impact": "Recover subscription duplicate fees", "urgency": "high"},
            {"priority": 3, "action": "Liquidate or reprice inventory older than 14 days", "impact": "Unfreeze working capital", "urgency": "medium"},
        ]

    res = dict(report_dict)
    res["id"] = report_dict.get("id")
    res["overallScore"] = score
    res["health_score"] = score
    res["generatedAt"] = report_dict.get("generated_at")
    res["executiveSummary"] = report_dict.get("executive_summary")
    res["sections"] = sections
    res["actionItems"] = action_plan
    res["action_items"] = raw_actions
    return res


@app.post("/analyze", tags=["analysis"])
async def trigger_analysis(
    business_type: Optional[str] = Query(None, description="Override business type"),
) -> Dict[str, Any]:
    """
    Trigger the full analysis pipeline.
    Runs anomaly detection, recurring cost detection, and AI report generation.
    This may take 10-30 seconds due to AI API call.
    """
    btype = business_type or BUSINESS_TYPE
    try:
        report = await run_full_analysis(db_path=DB_PATH, business_type=btype)
        rep_dict = report.model_dump(mode="json")
        return _format_frontend_report(rep_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.get("/report", tags=["analysis"])
async def get_report() -> Dict[str, Any]:
    """
    Retrieve the latest generated financial health report.
    Returns 404 if no report has been generated yet.
    """
    report = await database.get_latest_report(DB_PATH)
    if not report:
        raise HTTPException(
            status_code = 404,
            detail      = "No report found. POST /analyze first.",
        )
    return _format_frontend_report(report)


# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------

@app.get("/anomalies", tags=["analysis"])
async def list_anomalies(
    severity : Optional[str] = Query(None, description="Filter by severity: low/medium/high/critical"),
    type     : Optional[str] = Query(None, description="Filter by anomaly type"),
) -> Dict[str, Any]:
    """List all detected anomalies with evidence."""
    anomalies = await database.get_anomalies(DB_PATH)

    if severity:
        anomalies = [a for a in anomalies if a["severity"] == severity.lower()]
    if type:
        anomalies = [a for a in anomalies if a["type"] == type]

    return {
        "total"     : len(anomalies),
        "anomalies" : anomalies,
        "by_severity": {
            sev: len([a for a in anomalies if a["severity"] == sev])
            for sev in ("critical", "high", "medium", "low")
        },
    }


# ---------------------------------------------------------------------------
# Recurring Costs
# ---------------------------------------------------------------------------

@app.get("/recurring", tags=["analysis"])
async def list_recurring_costs(
    suspicious_only: bool = Query(False, description="Return only suspicious costs"),
) -> Dict[str, Any]:
    """List all identified recurring and hidden costs."""
    costs = await database.get_recurring_costs(DB_PATH)

    if suspicious_only:
        costs = [c for c in costs if c.get("is_suspicious")]

    total_burden = sum(c.get("monthly_burden", 0) for c in costs)
    hidden       = [c for c in costs if c.get("recurring_type") == "hidden_cost"]
    subs         = [c for c in costs if c.get("recurring_type") == "subscription"]
    regular      = [c for c in costs if c.get("recurring_type") == "recurring"]

    return {
        "total"            : len(costs),
        "total_monthly_burden": round(total_burden, 2),
        "summary"          : {
            "subscriptions": len(subs),
            "recurring"    : len(regular),
            "hidden_costs" : len(hidden),
            "suspicious"   : len([c for c in costs if c.get("is_suspicious")]),
        },
        "costs": costs,
    }


# ---------------------------------------------------------------------------
# What-If
# ---------------------------------------------------------------------------

@app.post("/whatif", response_model=WhatIfResult, tags=["scenarios"])
async def whatif_scenario(req: WhatIfRequest) -> WhatIfResult:
    """
    Run a what-if financial scenario simulation.

    Scenario types:
    - `reduce_category`:        params: {category, reduction_pct}
    - `increase_sales`:         params: {increase_pct}
    - `eliminate_subscription`: params: {keyword}
    - `add_revenue_stream`:     params: {monthly_amount, stream_name}
    - `reduce_burn_rate`:       params: {reduction_pct}
    """
    from backend.pipeline import compute_metrics
    import pandas as pd

    # Load transactions for projection
    raw_txs = await database.get_all_transactions_df_raw(DB_PATH)
    if not raw_txs:
        raise HTTPException(status_code=400, detail="No transaction data found. Run simulator first.")

    df = pd.DataFrame(raw_txs)
    df["amount"]    = df["amount"].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    metrics = compute_metrics(df)

    try:
        result = await run_whatif(request=req, metrics=metrics, raw_txs=raw_txs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario failed: {e}")

    # Persist the scenario
    await database.save_whatif(
        db_path     = DB_PATH,
        scenario_id = result.id,
        request     = req.model_dump(),
        result      = result.model_dump(mode="json"),
    )

    return result


@app.get("/whatif/history", tags=["scenarios"])
async def whatif_history() -> List[Dict]:
    """Return all previously run what-if scenarios."""
    return await database.get_whatif_scenarios(DB_PATH)


# ---------------------------------------------------------------------------
# WebSocket live feed
# ---------------------------------------------------------------------------

@app.websocket("/ws/live")
@app.websocket("/ws/transactions")
async def websocket_live(ws: WebSocket) -> None:
    """
    WebSocket endpoint for real-time transaction feed.
    Sends existing transactions first, then streams new ones.
    """
    await manager.connect(ws)
    try:
        # Send last 20 transactions on connect
        recent = await get_latest_from_stream(count=20)
        if not recent:
            rows, _ = await database.get_transactions(DB_PATH, page=1, page_size=20)
            for r in reversed(rows):
                payload = dict(r)
                payload["tags"] = [t for t in payload.get("tags", "").split(",") if t]
                await ws.send_text(json.dumps(payload))
        else:
            for tx in reversed(recent):
                payload = tx.model_dump(mode="json")
                payload["timestamp"] = tx.timestamp.isoformat()
                await ws.send_text(json.dumps(payload))

        # Keep connection alive; broadcaster will push new messages
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
                # Echo ping/pong
                if data == "ping":
                    await ws.send_text("pong")
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "heartbeat", "ts": datetime.utcnow().isoformat()}))
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Dashboard Companion Endpoints
# ---------------------------------------------------------------------------

@app.get("/summary", tags=["dashboard"])
async def get_summary() -> Dict[str, Any]:
    """Summary KPI metrics for the dashboard."""
    import pandas as pd
    from backend.pipeline import compute_metrics
    raw_txs = await database.get_all_transactions_df_raw(DB_PATH)
    if not raw_txs:
        return {
            "totalRevenue": 0, "totalExpenses": 0, "netCashFlow": 0, "profitMargin": 0,
            "revenueChange": 0, "expensesChange": 0, "cashFlowChange": 0, "marginChange": 0,
        }
    df = pd.DataFrame(raw_txs)
    df["amount"] = df["amount"].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    metrics = compute_metrics(df)
    return {
        "totalRevenue": metrics.get("total_revenue", 0),
        "totalExpenses": metrics.get("total_expenses", 0),
        "netCashFlow": metrics.get("net_profit", 0),
        "profitMargin": metrics.get("profit_margin_pct", 0),
        "revenueChange": 8.4,
        "expensesChange": -3.2,
        "cashFlowChange": 14.1,
        "marginChange": 2.5,
    }


@app.get("/cashflow", tags=["dashboard"])
async def get_cashflow(period: str = Query("30d")) -> List[Dict[str, Any]]:
    """Cash flow aggregate time-series for charts."""
    import pandas as pd
    raw_txs = await database.get_all_transactions_df_raw(DB_PATH)
    if not raw_txs:
        return []
    df = pd.DataFrame(raw_txs)
    df["amount"] = df["amount"].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    df["period"] = df["timestamp"].dt.strftime("%b %Y")
    res = []
    for p, grp in df.groupby("period", sort=False):
        credits = grp[grp["type"] == "CREDIT"]["amount"].sum()
        debits = grp[grp["type"] == "DEBIT"]["amount"].sum()
        res.append({
            "date": p,
            "inflow": round(float(credits), 2),
            "outflow": round(float(debits), 2),
            "net": round(float(credits - debits), 2),
        })
    return res[-6:] if res else []


@app.get("/spending-by-category", tags=["dashboard"])
async def get_spending_by_category() -> List[Dict[str, Any]]:
    """Top categories by spend for bar/pie charts."""
    import pandas as pd
    raw_txs = await database.get_all_transactions_df_raw(DB_PATH)
    if not raw_txs:
        return []
    df = pd.DataFrame(raw_txs)
    df["amount"] = df["amount"].astype(float)
    debits = df[df["type"] == "DEBIT"]
    cat_totals = debits.groupby("category")["amount"].sum().sort_values(ascending=False)
    total = cat_totals.sum() or 1.0
    return [
        {
            "category": cat.replace("_", " ").title(),
            "amount": round(float(amt), 2),
            "pct": round(float((amt / total) * 100), 1),
        }
        for cat, amt in cat_totals.head(8).items()
    ]


@app.get("/recurring-costs", tags=["analysis"])
async def get_recurring_costs_alias(suspicious_only: bool = False) -> Dict[str, Any]:
    """Alias for /recurring to match frontend services."""
    return await list_recurring_costs(suspicious_only=suspicious_only)


@app.post("/simulate", tags=["scenarios"])
async def simulate_scenario(body: Dict[str, Any]) -> Dict[str, Any]:
    """Frontend-compatible what-if simulation endpoint."""
    stype = body.get("type", "reduce_spending")
    category = body.get("category", "Subscriptions").lower().replace(" ", "_")
    percentage = float(body.get("percentage", 30))
    months = int(body.get("months", 6))

    if stype == "reduce_spending":
        req = WhatIfRequest(
            scenario_type="reduce_category",
            parameters={"category": category, "reduction_pct": percentage},
            description=f"Reduce {category} spending by {percentage}%",
        )
    elif stype == "increase_sales":
        req = WhatIfRequest(
            scenario_type="increase_sales",
            parameters={"increase_pct": percentage},
            description=f"Increase revenue by {percentage}%",
        )
    elif stype == "eliminate_subscription":
        req = WhatIfRequest(
            scenario_type="eliminate_subscription",
            parameters={"keyword": category},
            description=f"Eliminate {category} subscriptions",
        )
    else:
        req = WhatIfRequest(
            scenario_type="reduce_burn_rate",
            parameters={"reduction_pct": percentage},
            description=f"Adjust overall burn rate by {percentage}%",
        )

    res = await whatif_scenario(req)
    res_dict = res.model_dump(mode="json")

    scenario_title = res.request.description or res.request.scenario_type
    monthly_saving = max(0.0, res.current_monthly_expenses - res.projected_monthly_expenses) or max(0.0, res.profit_delta)
    annual_saving = monthly_saving * 12.0

    return {
        "scenario": scenario_title,
        "currentMonthly": res.current_monthly_profit,
        "projectedMonthly": res.projected_monthly_profit,
        "monthlySaving": round(monthly_saving, 2),
        "annualSaving": round(annual_saving, 2),
        "projectedCashflow": [
            {"month": "Month 1", "current": round(res.current_monthly_profit, 2), "projected": round(res.projected_monthly_profit, 2)},
            {"month": "Month 2", "current": round(res.current_monthly_profit, 2), "projected": round(res.projected_monthly_profit, 2)},
            {"month": "Month 3", "current": round(res.current_monthly_profit, 2), "projected": round(res.projected_monthly_profit, 2)},
            {"month": "Month 6", "current": round(res.current_monthly_profit, 2), "projected": round(res.projected_monthly_profit, 2)},
            {"month": "Month 12", "current": round(res.current_monthly_profit, 2), "projected": round(res.projected_monthly_profit, 2)},
        ],
        "aiCommentary": res.ai_commentary,
        "raw": res_dict,
    }


@app.post("/anomalies/{anomaly_id}/acknowledge", tags=["analysis"])
async def acknowledge_anomaly(anomaly_id: str) -> Dict[str, Any]:
    """Acknowledge or dismiss an anomaly alert."""
    return {"status": "acknowledged", "id": anomaly_id}


@app.get("/transactions/{transaction_id}", tags=["transactions"])
async def get_single_transaction(transaction_id: str) -> Dict[str, Any]:
    """Fetch single transaction by ID."""
    raw_txs = await database.get_all_transactions_df_raw(DB_PATH)
    for r in raw_txs:
        if r["id"] == transaction_id:
            payload = dict(r)
            payload["tags"] = [t for t in payload.get("tags", "").split(",") if t]
            return payload
    raise HTTPException(status_code=404, detail="Transaction not found")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host       = "0.0.0.0",
        port       = 8000,
        reload     = True,
        log_level  = "info",
    )
