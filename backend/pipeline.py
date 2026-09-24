"""
FinVisor 2.0 — Analysis Pipeline
==================================
Orchestrates the full analysis:
  1. Load all transactions from DB
  2. Compute financial health metrics
  3. Run anomaly detection
  4. Run recurring cost detection
  5. Identify good/bad transactions
  6. Call AI advisor to generate the report
  7. Persist results back to DB
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend import db as database
from backend.anomaly import run_anomaly_detection
from backend.recurring import detect_recurring_costs, total_monthly_burden
from simulator.schemas import (
    ActionItem,
    Anomaly,
    FinancialReport,
    RecurringCost,
    BusinessType,
    AnomalySeverity,
    RiskItem,
    CashFlowForecast,
)


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Derive key financial KPIs from a transaction DataFrame."""
    if df.empty:
        return {}

    credits = df[df["type"] == "CREDIT"]
    debits  = df[df["type"] == "DEBIT"]

    total_revenue  = float(credits["amount"].sum())
    total_expenses = float(debits["amount"].sum())
    net_profit     = total_revenue - total_expenses

    # Date range
    df["ts"]    = pd.to_datetime(df["timestamp"], format="ISO8601")
    period_start= df["ts"].min()
    period_end  = df["ts"].max()
    n_days      = max(1, (period_end - period_start).days)

    burn_rate_daily       = total_expenses / n_days
    average_daily_revenue = total_revenue  / n_days
    profit_margin_pct     = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # Cash runway: latest account balance / daily burn
    latest_balance = float(df.sort_values("ts").iloc[-1]["account_balance"])
    cash_runway    = latest_balance / burn_rate_daily if burn_rate_daily > 0 else None

    # Per-category breakdown
    cat_spend = debits.groupby("category")["amount"].sum().to_dict()

    # Daily revenue series
    credits_copy = credits.copy()
    credits_copy["date"] = pd.to_datetime(credits_copy["timestamp"], format="ISO8601").dt.date
    daily_revenue = credits_copy.groupby("date")["amount"].sum()

    # Good transactions: CREDIT within 7 days of an inventory_order DEBIT
    debits_copy = debits.copy()
    debits_copy["ts"] = pd.to_datetime(debits_copy["timestamp"], format="ISO8601")
    credits_copy["ts"] = pd.to_datetime(credits_copy["timestamp"], format="ISO8601")

    good_tx_ids: List[str] = []
    bad_tx_ids : List[str] = []
    orders = debits_copy[debits_copy["tags"].str.contains("inventory_order", na=False)]
    for _, order in orders.iterrows():
        window_end = order["ts"] + timedelta(days=7)
        quick_sales = credits_copy[
            (credits_copy["ts"] >= order["ts"]) &
            (credits_copy["ts"] <= window_end)
        ]
        if not quick_sales.empty:
            good_tx_ids.extend(quick_sales["id"].tolist())
        else:
            bad_tx_ids.append(order["id"])

    return {
        "total_revenue"         : round(total_revenue, 2),
        "total_expenses"        : round(total_expenses, 2),
        "net_profit"            : round(net_profit, 2),
        "profit_margin_pct"     : round(profit_margin_pct, 2),
        "burn_rate_daily"       : round(burn_rate_daily, 2),
        "average_daily_revenue" : round(average_daily_revenue, 2),
        "cash_runway_days"      : round(cash_runway, 1) if cash_runway else None,
        "latest_balance"        : round(latest_balance, 2),
        "period_start"          : period_start.isoformat(),
        "period_end"            : period_end.isoformat(),
        "n_days"                : n_days,
        "total_transactions"    : len(df),
        "category_breakdown"    : {k: round(float(v), 2) for k, v in cat_spend.items()},
        "daily_revenue_mean"    : round(float(daily_revenue.mean()), 2) if not daily_revenue.empty else 0,
        "daily_revenue_std"     : round(float(daily_revenue.std()), 2) if not daily_revenue.empty else 0,
        "good_tx_ids"           : good_tx_ids[:50],
        "bad_tx_ids"            : bad_tx_ids[:50],
    }


# ---------------------------------------------------------------------------
# Cash flow forecast
# ---------------------------------------------------------------------------

def build_cash_flow_forecast(metrics: Dict[str, Any]) -> CashFlowForecast:
    """Simple linear extrapolation for 30-day forecast."""
    daily_rev  = metrics.get("average_daily_revenue", 0)
    daily_burn = metrics.get("burn_rate_daily", 0)

    projected_inflow  = round(daily_rev  * 30, 2)
    projected_outflow = round(daily_burn * 30, 2)
    projected_net     = round(projected_inflow - projected_outflow, 2)

    # Confidence decreases with high revenue variance
    std   = metrics.get("daily_revenue_std", 0)
    mean  = metrics.get("daily_revenue_mean", 1)
    cv    = std / mean if mean > 0 else 1.0
    conf  = max(0.3, min(0.95, 1.0 - cv * 0.5))

    return CashFlowForecast(
        period_days       = 30,
        projected_inflow  = projected_inflow,
        projected_outflow = projected_outflow,
        projected_net     = projected_net,
        confidence        = round(conf, 2),
        assumptions       = [
            "Linear extrapolation of last period's average daily revenue",
            "Fixed costs assumed constant",
            "Seasonal effects not modelled",
            f"Based on {metrics.get('n_days', 0)} days of historical data",
        ],
    )


# ---------------------------------------------------------------------------
# Risk items builder
# ---------------------------------------------------------------------------

def build_risk_items(
    metrics  : Dict[str, Any],
    anomalies: List[Dict],
    recurring: List[Dict],
) -> List[RiskItem]:
    """Derive structured risk items from analysis outputs."""
    risks: List[RiskItem] = []

    # Liquidity risk
    runway = metrics.get("cash_runway_days")
    if runway is not None:
        if runway < 30:
            sev = AnomalySeverity.CRITICAL
        elif runway < 60:
            sev = AnomalySeverity.HIGH
        elif runway < 90:
            sev = AnomalySeverity.MEDIUM
        else:
            sev = AnomalySeverity.LOW
        risks.append(RiskItem(
            category    = "liquidity",
            description = f"Cash runway is {runway:.0f} days at current burn rate of ₹{metrics.get('burn_rate_daily',0):,.0f}/day",
            severity    = sev,
            evidence    = f"Latest balance ₹{metrics.get('latest_balance',0):,.2f}, burn rate ₹{metrics.get('burn_rate_daily',0):,.2f}/day",
        ))

    # Profitability risk
    margin = metrics.get("profit_margin_pct", 0)
    if margin < 0:
        risks.append(RiskItem(
            category    = "operational",
            description = f"Negative profit margin ({margin:.1f}%) — business is currently unprofitable",
            severity    = AnomalySeverity.CRITICAL,
            evidence    = f"Revenue ₹{metrics.get('total_revenue',0):,.2f} < Expenses ₹{metrics.get('total_expenses',0):,.2f}",
        ))
    elif margin < 5:
        risks.append(RiskItem(
            category    = "operational",
            description = f"Very thin profit margin ({margin:.1f}%) — highly vulnerable to cost increases",
            severity    = AnomalySeverity.HIGH,
            evidence    = f"Net profit ₹{metrics.get('net_profit',0):,.2f} on revenue ₹{metrics.get('total_revenue',0):,.2f}",
        ))

    # Anomaly-based risk
    critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
    if critical_anomalies:
        risks.append(RiskItem(
            category    = "operational",
            description = f"{len(critical_anomalies)} critical anomaly(ies) detected requiring immediate attention",
            severity    = AnomalySeverity.CRITICAL,
            evidence    = critical_anomalies[0].get("evidence", "See anomalies report"),
        ))

    # Recurring burden risk
    suspicious = [c for c in recurring if c.get("is_suspicious")]
    if suspicious:
        total_sus = sum(c.get("monthly_burden", 0) for c in suspicious)
        risks.append(RiskItem(
            category    = "operational",
            description = f"{len(suspicious)} suspicious recurring charge(s) costing ₹{total_sus:,.2f}/month",
            severity    = AnomalySeverity.HIGH,
            evidence    = "; ".join(
                f"{c['description']} ₹{c['average_amount']:,.2f} (tx: {c.get('transaction_ids',['?'])[0]})"
                for c in suspicious[:3]
            ),
        ))

    return risks


# ---------------------------------------------------------------------------
# Action items (non-AI fallback, always generated)
# ---------------------------------------------------------------------------

def build_action_items(
    metrics  : Dict[str, Any],
    anomalies: List[Dict],
    recurring: List[Dict],
) -> List[ActionItem]:
    items: List[ActionItem] = []
    priority = 1

    # 1. Address critical anomalies
    critical = [a for a in anomalies if a.get("severity") in ("critical", "high")][:3]
    if critical:
        items.append(ActionItem(
            priority         = priority,
            title            = f"Investigate {len(critical)} high-severity anomaly(ies)",
            description      = "; ".join(a["description"] for a in critical[:2]),
            transaction_refs = [a["transaction_id"] for a in critical],
            potential_saving = sum(a.get("metadata", {}).get("amount", 0) for a in critical),
        ))
        priority += 1

    # 2. Cancel suspicious subscriptions
    sus_subs = [c for c in recurring if c.get("is_suspicious") and c.get("monthly_burden", 0) > 0]
    if sus_subs:
        total = sum(c["monthly_burden"] for c in sus_subs)
        items.append(ActionItem(
            priority         = priority,
            title            = f"Cancel {len(sus_subs)} suspicious subscription(s)",
            description      = f"Total saving ₹{total:,.2f}/month. Items: "
                               + ", ".join(c["description"] for c in sus_subs[:3]),
            transaction_refs = [c["transaction_ids"][0] for c in sus_subs if c.get("transaction_ids")],
            potential_saving = total,
        ))
        priority += 1

    # 3. Address idle inventory
    idle = [a for a in anomalies if a.get("type") == "idle_inventory"]
    if idle:
        total_idle = sum(a.get("metadata", {}).get("order_amount", 0) for a in idle)
        items.append(ActionItem(
            priority         = priority,
            title            = f"Review {len(idle)} idle inventory order(s)",
            description      = f"₹{total_idle:,.2f} tied up in potentially unsold stock. "
                               "Review these orders and liquidate slow-moving items.",
            transaction_refs = [a["transaction_id"] for a in idle[:5]],
            potential_saving = total_idle * 0.3,   # assume 30% recovery
        ))
        priority += 1

    # 4. Revenue stability (if irregular income detected)
    irregular = [a for a in anomalies if a.get("type") == "irregular_income"]
    if irregular:
        items.append(ActionItem(
            priority         = priority,
            title            = "Stabilise revenue with retainer / advance payment model",
            description      = irregular[0]["description"],
            transaction_refs = [irregular[0]["transaction_id"]],
            potential_saving = None,
        ))
        priority += 1

    # 5. Reduce top spending category if margin is thin
    if metrics.get("profit_margin_pct", 100) < 10:
        cat_spend = metrics.get("category_breakdown", {})
        if cat_spend:
            top_cat, top_amt = max(cat_spend.items(), key=lambda x: x[1])
            items.append(ActionItem(
                priority         = priority,
                title            = f"Reduce '{top_cat}' spending",
                description      = f"'{top_cat}' is your highest expense at ₹{top_amt:,.2f}. "
                                   "A 10% reduction would significantly improve margins.",
                transaction_refs = [],
                potential_saving = top_amt * 0.10,
            ))

    return items[:5]


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

async def run_full_analysis(
    db_path      : str,
    business_type: str = "retailer",
) -> FinancialReport:
    """
    Run the complete analysis pipeline:
      load → metrics → anomaly detection → recurring → AI report → save
    Returns a FinancialReport object.
    """
    # 0. Ensure tables exist
    await database.init_db(db_path)

    # 1. Load transactions
    raw_txs = await database.get_all_transactions_df_raw(db_path)
    if not raw_txs:
        raise ValueError("No transactions found in the database. Run the simulator first.")

    df = pd.DataFrame(raw_txs)
    df["amount"]    = df["amount"].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")

    # 2. Compute metrics
    metrics = compute_metrics(df)
    metrics["business_type"] = business_type

    # 3. Anomaly detection
    anomalies = run_anomaly_detection(raw_txs)
    metrics["anomaly_count"] = len(anomalies)

    # Persist anomalies
    anomaly_dicts = [
        {
            "id"            : a.id,
            "transaction_id": a.transaction_id,
            "type"          : a.type.value,
            "severity"      : a.severity.value,
            "description"   : a.description,
            "evidence"      : a.evidence,
            "detected_at"   : a.detected_at.isoformat(),
            "metadata"      : a.metadata,
        }
        for a in anomalies
    ]
    await database.upsert_anomalies(db_path, anomaly_dicts)

    # 4. Recurring cost detection
    recurring = detect_recurring_costs(raw_txs)
    metrics["recurring_cost_count"] = len(recurring)

    recurring_dicts = [
        {
            "id"              : r.id,
            "category"        : r.category,
            "description"     : r.description,
            "merchant"        : r.merchant,
            "recurring_type"  : r.recurring_type.value,
            "frequency_days"  : r.frequency_days,
            "average_amount"  : r.average_amount,
            "total_paid"      : r.total_paid,
            "occurrence_count": r.occurrence_count,
            "transaction_ids" : r.transaction_ids,
            "is_necessary"    : r.is_necessary,
            "is_suspicious"   : r.is_suspicious,
            "monthly_burden"  : r.monthly_burden,
            "first_seen"      : r.first_seen.isoformat() if hasattr(r.first_seen, "isoformat") else str(r.first_seen),
            "last_seen"       : r.last_seen.isoformat()  if hasattr(r.last_seen,  "isoformat") else str(r.last_seen),
            "notes"           : r.notes,
        }
        for r in recurring
    ]
    await database.upsert_recurring_costs(db_path, recurring_dicts)

    # 5. Build structured items (non-AI)
    cash_flow  = build_cash_flow_forecast(metrics)
    risk_items = build_risk_items(metrics, anomaly_dicts, recurring_dicts)
    action_items_fallback = build_action_items(metrics, anomaly_dicts, recurring_dicts)

    # 6. AI report generation (imports here to avoid circular deps at startup)
    from backend.advisor import generate_financial_report
    ai_data = await generate_financial_report(
        metrics      = metrics,
        anomalies    = anomaly_dicts,
        recurring    = recurring_dicts,
        transactions = raw_txs,
        business_type= business_type,
    )

    # Merge AI action items with fallback
    ai_action_items: List[ActionItem] = []
    for item in ai_data.get("action_items", [])[:5]:
        try:
            ai_action_items.append(ActionItem(**item))
        except Exception:
            pass
    final_actions = ai_action_items or action_items_fallback

    # AI risk items
    ai_risk_items: List[RiskItem] = []
    for ri in ai_data.get("risk_items", []):
        try:
            ai_risk_items.append(RiskItem(**ri))
        except Exception:
            pass
    final_risks = ai_risk_items or risk_items

    # AI cash flow forecast
    ai_cf = ai_data.get("cash_flow_forecast")
    if ai_cf:
        try:
            cash_flow = CashFlowForecast(**ai_cf)
        except Exception:
            pass

    # 7. Assemble report
    report = FinancialReport(
        id                    = f"RPT-{uuid.uuid4().hex[:10].upper()}",
        generated_at          = datetime.utcnow(),
        business_type         = BusinessType(business_type),
        period_start          = datetime.fromisoformat(metrics["period_start"]),
        period_end            = datetime.fromisoformat(metrics["period_end"]),
        total_revenue         = metrics["total_revenue"],
        total_expenses        = metrics["total_expenses"],
        net_profit            = metrics["net_profit"],
        profit_margin_pct     = metrics["profit_margin_pct"],
        burn_rate_daily       = metrics["burn_rate_daily"],
        average_daily_revenue = metrics["average_daily_revenue"],
        cash_runway_days      = metrics.get("cash_runway_days"),
        total_transactions    = metrics["total_transactions"],
        anomaly_count         = metrics["anomaly_count"],
        recurring_cost_count  = metrics["recurring_cost_count"],
        executive_summary     = ai_data.get("executive_summary", "Analysis complete."),
        spending_analysis     = ai_data.get("spending_analysis", ""),
        risk_assessment       = ai_data.get("risk_assessment", ""),
        action_items          = final_actions,
        cash_flow_forecast    = cash_flow,
        risk_items            = final_risks,
        full_report_markdown  = ai_data.get("executive_summary", ""),
    )

    # 8. Persist report
    report_dict = report.model_dump(mode="json")
    await database.save_report(db_path, report_dict)

    return report
