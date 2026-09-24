"""
FinVisor 2.0 — SQLite Database Layer
=====================================
Uses aiosqlite for async access.  All tables are created on startup.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

# ---------------------------------------------------------------------------
# DB path (relative to project root; overridden by env var in main.py)
# ---------------------------------------------------------------------------
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "finvisor.db"

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL_TRANSACTIONS = """
CREATE TABLE IF NOT EXISTS transactions (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    amount          REAL NOT NULL,
    type            TEXT NOT NULL,
    category        TEXT NOT NULL,
    description     TEXT NOT NULL,
    account_balance REAL NOT NULL,
    business_type   TEXT NOT NULL,
    tags            TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_tx_category  ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_tx_type      ON transactions(type);
"""

_DDL_ANOMALIES = """
CREATE TABLE IF NOT EXISTS anomalies (
    id             TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    type           TEXT NOT NULL,
    severity       TEXT NOT NULL,
    description    TEXT NOT NULL,
    evidence       TEXT NOT NULL,
    detected_at    TEXT NOT NULL,
    metadata       TEXT NOT NULL DEFAULT '{}'
);
"""

_DDL_RECURRING = """
CREATE TABLE IF NOT EXISTS recurring_costs (
    id                 TEXT PRIMARY KEY,
    category           TEXT NOT NULL,
    description        TEXT NOT NULL,
    merchant           TEXT,
    recurring_type     TEXT NOT NULL,
    frequency_days     REAL,
    average_amount     REAL NOT NULL,
    total_paid         REAL NOT NULL,
    occurrence_count   INTEGER NOT NULL,
    transaction_ids    TEXT NOT NULL DEFAULT '[]',
    is_necessary       INTEGER NOT NULL DEFAULT 1,
    is_suspicious      INTEGER NOT NULL DEFAULT 0,
    monthly_burden     REAL NOT NULL DEFAULT 0,
    first_seen         TEXT NOT NULL,
    last_seen          TEXT NOT NULL,
    notes              TEXT NOT NULL DEFAULT ''
);
"""

_DDL_REPORTS = """
CREATE TABLE IF NOT EXISTS reports (
    id              TEXT PRIMARY KEY,
    generated_at    TEXT NOT NULL,
    business_type   TEXT NOT NULL,
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    data            TEXT NOT NULL   -- full JSON blob of FinancialReport
);
"""

_DDL_WHATIF = """
CREATE TABLE IF NOT EXISTS whatif_scenarios (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    request     TEXT NOT NULL,   -- JSON
    result      TEXT NOT NULL    -- JSON
);
"""


# ---------------------------------------------------------------------------
# Initialiser
# ---------------------------------------------------------------------------

async def init_db(db_path: str = str(DEFAULT_DB_PATH)) -> None:
    """Create all tables.  Called once at FastAPI startup."""
    async with aiosqlite.connect(db_path) as db:
        for ddl in (_DDL_TRANSACTIONS, _DDL_ANOMALIES, _DDL_RECURRING,
                    _DDL_REPORTS, _DDL_WHATIF):
            await db.executescript(ddl)
        await db.commit()


# ---------------------------------------------------------------------------
# Transaction helpers
# ---------------------------------------------------------------------------

async def get_transactions(
    db_path   : str,
    page      : int = 1,
    page_size : int = 50,
    tx_type   : Optional[str] = None,
    category  : Optional[str] = None,
    start_date: Optional[str] = None,
    end_date  : Optional[str] = None,
) -> Tuple[List[Dict], int]:
    """Return paginated transactions with optional filters."""
    conditions: List[str] = []
    params    : List[Any] = []

    if tx_type:
        conditions.append("type = ?")
        params.append(tx_type.upper())
    if category:
        conditions.append("category = ?")
        params.append(category)
    if start_date:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("timestamp <= ?")
        params.append(end_date)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        # Total count
        async with db.execute(
            f"SELECT COUNT(*) FROM transactions {where}", params
        ) as cur:
            row   = await cur.fetchone()
            total = row[0] if row else 0

        # Paginated rows
        offset = (page - 1) * page_size
        async with db.execute(
            f"SELECT * FROM transactions {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ) as cur:
            rows = await cur.fetchall()

    return [dict(r) for r in rows], total


async def get_all_transactions_df_raw(db_path: str) -> List[Dict]:
    """Fetch ALL transactions as list of dicts (for pipeline use)."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM transactions ORDER BY timestamp ASC"
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Anomaly helpers
# ---------------------------------------------------------------------------

async def upsert_anomalies(db_path: str, anomalies: List[Dict]) -> None:
    async with aiosqlite.connect(db_path) as db:
        for a in anomalies:
            await db.execute("""
                INSERT OR REPLACE INTO anomalies
                (id, transaction_id, type, severity, description, evidence, detected_at, metadata)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                a["id"], a["transaction_id"], a["type"], a["severity"],
                a["description"], a["evidence"], a["detected_at"],
                json.dumps(a.get("metadata", {})),
            ))
        await db.commit()


async def get_anomalies(db_path: str) -> List[Dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM anomalies ORDER BY detected_at DESC"
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["metadata"] = json.loads(d.get("metadata", "{}"))
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Recurring cost helpers
# ---------------------------------------------------------------------------

async def upsert_recurring_costs(db_path: str, costs: List[Dict]) -> None:
    async with aiosqlite.connect(db_path) as db:
        for c in costs:
            await db.execute("""
                INSERT OR REPLACE INTO recurring_costs
                (id, category, description, merchant, recurring_type,
                 frequency_days, average_amount, total_paid, occurrence_count,
                 transaction_ids, is_necessary, is_suspicious,
                 monthly_burden, first_seen, last_seen, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                c["id"], c["category"], c["description"], c.get("merchant"),
                c["recurring_type"], c.get("frequency_days"),
                c["average_amount"], c["total_paid"], c["occurrence_count"],
                json.dumps(c.get("transaction_ids", [])),
                int(c.get("is_necessary", True)),
                int(c.get("is_suspicious", False)),
                c.get("monthly_burden", 0),
                c["first_seen"], c["last_seen"], c.get("notes", ""),
            ))
        await db.commit()


async def get_recurring_costs(db_path: str) -> List[Dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM recurring_costs ORDER BY monthly_burden DESC"
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["transaction_ids"] = json.loads(d.get("transaction_ids", "[]"))
        d["is_necessary"]    = bool(d["is_necessary"])
        d["is_suspicious"]   = bool(d["is_suspicious"])
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

async def save_report(db_path: str, report: Dict) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT OR REPLACE INTO reports
            (id, generated_at, business_type, period_start, period_end, data)
            VALUES (?,?,?,?,?,?)
        """, (
            report["id"], report["generated_at"], report["business_type"],
            report["period_start"], report["period_end"],
            json.dumps(report),
        ))
        await db.commit()


async def get_latest_report(db_path: str) -> Optional[Dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT data FROM reports ORDER BY generated_at DESC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
    if row:
        return json.loads(row["data"])
    return None


# ---------------------------------------------------------------------------
# What-If helpers
# ---------------------------------------------------------------------------

async def save_whatif(db_path: str, scenario_id: str, request: Dict, result: Dict) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT OR REPLACE INTO whatif_scenarios (id, created_at, request, result)
            VALUES (?,?,?,?)
        """, (
            scenario_id,
            datetime.utcnow().isoformat(),
            json.dumps(request),
            json.dumps(result),
        ))
        await db.commit()


async def get_whatif_scenarios(db_path: str) -> List[Dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, created_at, request, result FROM whatif_scenarios ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
    return [{
        "id"        : r["id"],
        "created_at": r["created_at"],
        "request"   : json.loads(r["request"]),
        "result"    : json.loads(r["result"]),
    } for r in rows]
