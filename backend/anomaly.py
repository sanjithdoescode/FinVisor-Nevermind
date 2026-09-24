"""
FinVisor 2.0 — Anomaly Detection Engine
=========================================
Detects the following anomaly types from a list of transactions:

  1. STATISTICAL_OUTLIER  — Z-score > 2.5 on amount within category
  2. DUPLICATE_PAYMENT    — same amount + category within 24 h
  3. UNUSUAL_TIMING       — transactions between 01:00–04:00
  4. BUDGET_VIOLATION     — category total > configurable threshold
  5. IDLE_INVENTORY       — inventory order with no matching sale for >14 days
  6. IRREGULAR_INCOME     — high coefficient of variation in daily revenue

All anomalies carry specific transaction IDs and amounts in their evidence.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from simulator.schemas import Anomaly, AnomalySeverity, AnomalyType

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

# Per-category monthly budget caps (₹).  If missing, no cap is applied.
CATEGORY_BUDGETS: Dict[str, float] = {
    "marketing"         : 80_000,
    "logistics"         : 50_000,
    "maintenance"       : 30_000,
    "travel"            : 40_000,
    "office_supplies"   : 15_000,
    "waste_disposal"    : 10_000,
    "health_inspection" : 8_000,
    "legal_fees"        : 60_000,
}

ZSCORE_THRESHOLD   = 2.5   # standard deviations for outlier
UNUSUAL_HOUR_START = 1     # 01:00
UNUSUAL_HOUR_END   = 4     # 04:00 (exclusive)
IDLE_INVENTORY_DAYS= 14    # orders unresolved after this → anomaly
INCOME_CV_THRESHOLD= 0.75  # coefficient of variation for irregular income


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _severity_from_zscore(z: float) -> AnomalySeverity:
    if z >= 4.0:
        return AnomalySeverity.CRITICAL
    if z >= 3.0:
        return AnomalySeverity.HIGH
    if z >= 2.5:
        return AnomalySeverity.MEDIUM
    return AnomalySeverity.LOW


def _new_id() -> str:
    return f"ANO-{uuid.uuid4().hex[:10].upper()}"


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------

def detect_statistical_outliers(df: pd.DataFrame) -> List[Anomaly]:
    """Z-score analysis per category on DEBIT transactions."""
    anomalies: List[Anomaly] = []
    debits = df[df["type"] == "DEBIT"].copy()
    if debits.empty:
        return anomalies

    for cat, grp in debits.groupby("category"):
        if len(grp) < 5:   # too few samples for meaningful stats
            continue
        amounts = grp["amount"].values.astype(float)
        mean, std = amounts.mean(), amounts.std()
        if std == 0:
            continue

        for _, row in grp.iterrows():
            z = abs((row["amount"] - mean) / std)
            if z >= ZSCORE_THRESHOLD:
                sev = _severity_from_zscore(z)
                anomalies.append(Anomaly(
                    id             = _new_id(),
                    transaction_id = row["id"],
                    type           = AnomalyType.STATISTICAL_OUTLIER,
                    severity       = sev,
                    description    = (
                        f"Unusually large {cat} expense: ₹{row['amount']:,.2f} "
                        f"(category avg ₹{mean:,.2f}, z-score {z:.1f})"
                    ),
                    evidence       = (
                        f"Transaction {row['id']} amount ₹{row['amount']:,.2f} "
                        f"is {z:.1f}σ above the mean for '{cat}' "
                        f"(μ=₹{mean:,.2f}, σ=₹{std:,.2f}, n={len(grp)})"
                    ),
                    metadata       = {
                        "category": cat,
                        "z_score" : round(float(z), 2),
                        "mean"    : round(float(mean), 2),
                        "std"     : round(float(std), 2),
                    },
                ))
    return anomalies


def detect_duplicate_payments(df: pd.DataFrame) -> List[Anomaly]:
    """Find DEBIT transactions with same amount + category within 24 hours."""
    anomalies: List[Anomaly] = []
    debits = df[df["type"] == "DEBIT"].copy()
    if debits.empty:
        return anomalies

    debits = debits.sort_values("timestamp")
    seen   : set = set()   # (tx_id1, tx_id2) pairs already flagged

    for i, row_a in debits.iterrows():
        window = debits[
            (debits["timestamp"] > row_a["timestamp"]) &
            (debits["timestamp"] <= row_a["timestamp"] + timedelta(hours=24)) &
            (debits["category"] == row_a["category"]) &
            (debits["amount"]   == row_a["amount"]) &
            (debits.index        != i)
        ]
        for j, row_b in window.iterrows():
            pair = tuple(sorted([row_a["id"], row_b["id"]]))
            if pair in seen:
                continue
            seen.add(pair)

            delta_h = (row_b["timestamp"] - row_a["timestamp"]).total_seconds() / 3600
            anomalies.append(Anomaly(
                id             = _new_id(),
                transaction_id = row_b["id"],
                type           = AnomalyType.DUPLICATE_PAYMENT,
                severity       = AnomalySeverity.HIGH,
                description    = (
                    f"Possible duplicate {row_a['category']} payment of "
                    f"₹{row_a['amount']:,.2f} within {delta_h:.1f} hours"
                ),
                evidence       = (
                    f"Transaction {row_b['id']} (₹{row_b['amount']:,.2f}, "
                    f"{row_b['timestamp']}) duplicates {row_a['id']} "
                    f"(₹{row_a['amount']:,.2f}, {row_a['timestamp']}) — "
                    f"same category '{row_a['category']}', "
                    f"gap {delta_h:.1f} h"
                ),
                metadata       = {
                    "original_tx_id" : row_a["id"],
                    "duplicate_tx_id": row_b["id"],
                    "amount"         : float(row_a["amount"]),
                    "gap_hours"      : round(delta_h, 2),
                },
            ))
    return anomalies


def detect_unusual_timing(df: pd.DataFrame) -> List[Anomaly]:
    """Flag transactions occurring between 01:00 and 04:00 on DEBIT side."""
    anomalies: List[Anomaly] = []
    debits = df[df["type"] == "DEBIT"].copy()
    if debits.empty:
        return anomalies

    # Ensure timestamp is datetime
    debits["ts_dt"] = pd.to_datetime(debits["timestamp"], format="ISO8601")
    night = debits[
        (debits["ts_dt"].dt.hour >= UNUSUAL_HOUR_START) &
        (debits["ts_dt"].dt.hour <  UNUSUAL_HOUR_END)
    ]

    for _, row in night.iterrows():
        anomalies.append(Anomaly(
            id             = _new_id(),
            transaction_id = row["id"],
            type           = AnomalyType.UNUSUAL_TIMING,
            severity       = AnomalySeverity.MEDIUM,
            description    = (
                f"Expense of ₹{row['amount']:,.2f} in '{row['category']}' "
                f"at {row['ts_dt'].strftime('%H:%M')} — unusual off-hours"
            ),
            evidence       = (
                f"Transaction {row['id']} posted at "
                f"{row['ts_dt'].strftime('%Y-%m-%d %H:%M')} "
                f"(between {UNUSUAL_HOUR_START:02d}:00 and {UNUSUAL_HOUR_END:02d}:00), "
                f"amount ₹{row['amount']:,.2f}, category '{row['category']}'"
            ),
            metadata       = {
                "hour"    : int(row["ts_dt"].dt.hour) if hasattr(row["ts_dt"], "dt") else row["ts_dt"].hour,
                "category": row["category"],
            },
        ))
    return anomalies


def detect_budget_violations(df: pd.DataFrame) -> List[Anomaly]:
    """Flag categories that exceed their monthly budget cap."""
    anomalies: List[Anomaly] = []
    debits = df[df["type"] == "DEBIT"].copy()
    if debits.empty:
        return anomalies

    debits["month"] = pd.to_datetime(debits["timestamp"], format="ISO8601").dt.to_period("M")

    for (cat, month), grp in debits.groupby(["category", "month"]):
        cap = CATEGORY_BUDGETS.get(cat)
        if cap is None:
            continue
        total = grp["amount"].sum()
        if total > cap:
            tx_ids = grp["id"].tolist()
            pct    = (total / cap - 1) * 100
            sev    = (AnomalySeverity.CRITICAL if pct > 100
                      else AnomalySeverity.HIGH if pct > 50
                      else AnomalySeverity.MEDIUM)
            anomalies.append(Anomaly(
                id             = _new_id(),
                transaction_id = tx_ids[0],
                type           = AnomalyType.BUDGET_VIOLATION,
                severity       = sev,
                description    = (
                    f"'{cat}' spending ₹{total:,.2f} exceeded budget "
                    f"₹{cap:,.2f} by {pct:.0f}% in {month}"
                ),
                evidence       = (
                    f"Month {month}: {len(tx_ids)} transactions in '{cat}' "
                    f"totalling ₹{total:,.2f} vs budget ₹{cap:,.2f}. "
                    f"Transactions: {', '.join(tx_ids[:5])}"
                    + (f" … (+{len(tx_ids)-5} more)" if len(tx_ids) > 5 else "")
                ),
                metadata       = {
                    "category"    : cat,
                    "month"       : str(month),
                    "total_spent" : round(float(total), 2),
                    "budget"      : cap,
                    "overage_pct" : round(pct, 1),
                    "tx_ids"      : tx_ids[:10],
                },
            ))
    return anomalies


def detect_idle_inventory(df: pd.DataFrame) -> List[Anomaly]:
    """
    Detect inventory/raw_material orders with no matching sale within
    IDLE_INVENTORY_DAYS days (tag = 'inventory_order').
    """
    anomalies: List[Anomaly] = []
    df["ts_dt"] = pd.to_datetime(df["timestamp"], format="ISO8601")

    orders = df[
        df["tags"].str.contains("inventory_order", na=False) &
        (df["type"] == "DEBIT")
    ].copy()

    if orders.empty:
        return anomalies

    # Proxy: check if a CREDIT sale occurs within 14 days of the order date
    credits = df[df["type"] == "CREDIT"].copy()

    for _, order in orders.iterrows():
        window_end   = order["ts_dt"] + timedelta(days=IDLE_INVENTORY_DAYS)
        subsequent   = credits[
            (credits["ts_dt"] >= order["ts_dt"]) &
            (credits["ts_dt"] <= window_end)
        ]
        if subsequent.empty:
            anomalies.append(Anomaly(
                id             = _new_id(),
                transaction_id = order["id"],
                type           = AnomalyType.IDLE_INVENTORY,
                severity       = AnomalySeverity.MEDIUM,
                description    = (
                    f"Inventory order ₹{order['amount']:,.2f} "
                    f"({order['category']}) on {order['ts_dt'].strftime('%Y-%m-%d')} "
                    f"with no recorded sales in next {IDLE_INVENTORY_DAYS} days"
                ),
                evidence       = (
                    f"Transaction {order['id']} placed ₹{order['amount']:,.2f} "
                    f"inventory order on {order['ts_dt'].strftime('%Y-%m-%d')}. "
                    f"No CREDIT sales found within {IDLE_INVENTORY_DAYS} days window "
                    f"({order['ts_dt'].strftime('%Y-%m-%d')} → "
                    f"{window_end.strftime('%Y-%m-%d')}). "
                    "Possible unsold/wasted stock."
                ),
                metadata       = {
                    "order_date"    : order["ts_dt"].isoformat(),
                    "order_amount"  : float(order["amount"]),
                    "category"      : order["category"],
                    "window_days"   : IDLE_INVENTORY_DAYS,
                },
            ))
    return anomalies


def detect_irregular_income(df: pd.DataFrame) -> List[Anomaly]:
    """
    Detect feast/famine income patterns by computing coefficient of
    variation on daily revenue.  High CV → irregular income.
    """
    anomalies: List[Anomaly] = []
    credits = df[df["type"] == "CREDIT"].copy()
    if credits.empty:
        return anomalies

    credits["date"] = pd.to_datetime(credits["timestamp"], format="ISO8601").dt.date
    daily = credits.groupby("date")["amount"].sum()

    if len(daily) < 14:
        return anomalies   # need at least 2 weeks of data

    cv = daily.std() / daily.mean()
    if cv >= INCOME_CV_THRESHOLD:
        worst_day  = daily.idxmin()
        best_day   = daily.idxmax()
        sample_ids = credits[credits["date"] == worst_day]["id"].tolist()[:3]
        sev        = (AnomalySeverity.HIGH if cv > 1.2
                      else AnomalySeverity.MEDIUM)
        anomalies.append(Anomaly(
            id             = _new_id(),
            transaction_id = sample_ids[0] if sample_ids else df.iloc[0]["id"],
            type           = AnomalyType.IRREGULAR_INCOME,
            severity       = sev,
            description    = (
                f"Irregular income pattern detected: daily revenue CV={cv:.2f} "
                f"(threshold {INCOME_CV_THRESHOLD}). "
                f"Best day ₹{daily[best_day]:,.2f}, worst ₹{daily[worst_day]:,.2f}"
            ),
            evidence       = (
                f"Over {len(daily)} trading days, daily revenue ranges from "
                f"₹{daily.min():,.2f} ({worst_day}) to ₹{daily.max():,.2f} ({best_day}). "
                f"CV={cv:.2f} indicates feast/famine cycles. "
                f"Worst-day sample transactions: {', '.join(sample_ids)}"
            ),
            metadata       = {
                "cv"           : round(float(cv), 3),
                "mean_daily"   : round(float(daily.mean()), 2),
                "std_daily"    : round(float(daily.std()), 2),
                "min_day"      : str(worst_day),
                "max_day"      : str(best_day),
                "n_days"       : len(daily),
            },
        ))
    return anomalies


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_anomaly_detection(raw_transactions: List[Dict]) -> List[Anomaly]:
    """
    Run all anomaly detectors on a list of transaction dicts.
    Returns deduplicated list of Anomaly objects.
    """
    if not raw_transactions:
        return []

    df = pd.DataFrame(raw_transactions)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    df["amount"]    = df["amount"].astype(float)
    df["tags"]      = df["tags"].fillna("")

    all_anomalies: List[Anomaly] = []
    all_anomalies.extend(detect_statistical_outliers(df))
    all_anomalies.extend(detect_duplicate_payments(df))
    all_anomalies.extend(detect_unusual_timing(df))
    all_anomalies.extend(detect_budget_violations(df))
    all_anomalies.extend(detect_idle_inventory(df))
    all_anomalies.extend(detect_irregular_income(df))

    return all_anomalies
