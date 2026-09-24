"""
FinVisor 2.0 — Recurring Cost Detection
=========================================
Identifies recurring expenses, subscriptions, and hidden costs from
raw transaction history.

Detection logic
---------------
1. Group DEBIT transactions by (description_stem, category).
2. If a group has ≥ 2 occurrences with consistent amounts → recurring/subscription.
3. If individual amounts are small (< ₹2,000) but occur ≥ 3 times → hidden cost.
4. Compute average inter-arrival gap to determine frequency_days.
5. Normalise to monthly_burden (30-day equivalent cost).
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from simulator.schemas import RecurringCost, RecurringType

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

HIDDEN_COST_MAX_AMOUNT   = 2_000   # ₹ — amounts below this are "small"
HIDDEN_COST_MIN_COUNT    = 3       # must occur at least this many times
SUBSCRIPTION_CV_THRESHOLD= 0.10    # coefficient of variation — low = fixed amount
RECURRING_MIN_COUNT      = 2       # minimum occurrences to qualify as recurring
SUSPICIOUS_KEYWORDS      = ["unknown", "misc", "other", "auto-charge", "duplicate",
                             "upgrade", "addon"]

# Subscription merchants (exact or partial matches against description)
KNOWN_SUBSCRIPTIONS = [
    "shopify", "quickbooks", "slack", "google workspace", "zoom",
    "github", "jira", "aws", "gcp", "azure", "salesforce", "hubspot",
    "zomato pro", "swiggy partner", "petpooja", "dropbox", "linkedin",
    "grammarly", "canva", "zoominfo",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id() -> str:
    return f"REC-{uuid.uuid4().hex[:10].upper()}"


def _stem_description(desc: str) -> str:
    """Normalise a description to a canonical 'stem' for grouping."""
    d = desc.lower().strip()
    # Remove date-like suffixes: "- Jan 2024", "(Feb 2025)", etc.
    d = re.sub(r"[-–]\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{4}", "", d)
    d = re.sub(r"\b\d{4}\b", "", d)
    d = re.sub(r"\b\d{1,2}/\d{1,2}\b", "", d)
    # Remove order/invoice numbers
    d = re.sub(r"#[\w\-]+", "", d)
    d = re.sub(r"\[.*?\]", "", d)    # strip [ANOMALY], [DUPLICATE] prefixes
    d = re.sub(r"\(.*?\)", "", d)    # strip parenthetical notes
    d = re.sub(r"\s+", " ", d).strip()
    return d


def _is_subscription(desc_lower: str) -> bool:
    return any(kw in desc_lower for kw in KNOWN_SUBSCRIPTIONS)


def _is_suspicious(desc_lower: str, is_hidden: bool) -> bool:
    if any(kw in desc_lower for kw in SUSPICIOUS_KEYWORDS):
        return True
    if is_hidden and desc_lower.count("duplicate") > 0:
        return True
    return False


def _compute_frequency(timestamps: pd.Series) -> Optional[float]:
    """Compute average inter-arrival gap in days."""
    sorted_ts = sorted(timestamps)
    if len(sorted_ts) < 2:
        return None
    gaps = [(sorted_ts[i+1] - sorted_ts[i]).days for i in range(len(sorted_ts)-1)]
    return float(np.mean(gaps)) if gaps else None


def _monthly_burden(avg_amount: float, freq_days: Optional[float]) -> float:
    """Project cost into 30-day equivalent."""
    if not freq_days or freq_days <= 0:
        return 0.0
    return round(avg_amount * (30.0 / freq_days), 2)


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def detect_recurring_costs(raw_transactions: List[Dict]) -> List[RecurringCost]:
    """
    Identify recurring costs, subscriptions, and hidden costs from a
    list of transaction dicts.  Returns a list of RecurringCost objects.
    """
    if not raw_transactions:
        return []

    df = pd.DataFrame(raw_transactions)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    df["amount"]    = df["amount"].astype(float)
    df["tags"]      = df["tags"].fillna("")

    # Work only on DEBIT transactions
    debits = df[df["type"] == "DEBIT"].copy()
    if debits.empty:
        return []

    # Add stemmed description for grouping
    debits["stem"] = debits["description"].apply(_stem_description)

    # Group by (stem, category)
    groups = debits.groupby(["stem", "category"])

    results: List[RecurringCost] = []

    for (stem, category), grp in groups:
        if len(grp) < RECURRING_MIN_COUNT:
            continue

        amounts    = grp["amount"].values.astype(float)
        mean_amt   = float(np.mean(amounts))
        std_amt    = float(np.std(amounts))
        cv         = std_amt / mean_amt if mean_amt > 0 else 1.0
        total_paid = float(np.sum(amounts))
        freq_days  = _compute_frequency(grp["timestamp"])
        tx_ids     = grp["id"].tolist()
        first_seen = grp["timestamp"].min()
        last_seen  = grp["timestamp"].max()
        desc_lower = stem.lower()

        # Determine recurring type
        if _is_subscription(desc_lower) or (cv <= SUBSCRIPTION_CV_THRESHOLD and freq_days and 25 <= freq_days <= 35):
            rec_type = RecurringType.SUBSCRIPTION
        elif mean_amt <= HIDDEN_COST_MAX_AMOUNT and len(grp) >= HIDDEN_COST_MIN_COUNT:
            rec_type = RecurringType.HIDDEN_COST
        else:
            rec_type = RecurringType.RECURRING

        # Determine merchant name from stem
        merchant = stem.split(" subscription")[0].split(" -")[0].strip().title() or None

        # is_suspicious flags
        is_suspicious = _is_suspicious(desc_lower, is_hidden=(rec_type == RecurringType.HIDDEN_COST))

        # is_necessary: subs/rent/utilities assumed necessary; hidden costs are not
        is_necessary = rec_type in (RecurringType.SUBSCRIPTION, RecurringType.RECURRING)
        if is_suspicious:
            is_necessary = False

        # Monthly burden
        m_burden = _monthly_burden(mean_amt, freq_days)

        # Build notes
        notes_parts = []
        if cv > 0.15:
            notes_parts.append(f"Variable amounts (CV={cv:.2f})")
        if freq_days:
            notes_parts.append(f"Avg every {freq_days:.0f} days")
        if is_suspicious:
            notes_parts.append("⚠ Suspicious — review recommended")
        if rec_type == RecurringType.HIDDEN_COST:
            notes_parts.append(
                f"Small recurring charge: {len(grp)}× ₹{mean_amt:,.2f} "
                f"= ₹{total_paid:,.2f} total so far"
            )

        results.append(RecurringCost(
            id                  = _new_id(),
            category            = category,
            description         = stem.title(),
            merchant            = merchant,
            recurring_type      = rec_type,
            frequency_days      = round(freq_days, 1) if freq_days else None,
            average_amount      = round(mean_amt, 2),
            total_paid          = round(total_paid, 2),
            occurrence_count    = int(len(grp)),
            transaction_ids     = tx_ids,
            is_necessary        = is_necessary,
            is_suspicious       = is_suspicious,
            monthly_burden      = m_burden,
            first_seen          = first_seen,
            last_seen           = last_seen,
            notes               = " | ".join(notes_parts),
        ))

    # Sort by monthly_burden descending
    results.sort(key=lambda r: r.monthly_burden, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Convenience aggregations
# ---------------------------------------------------------------------------

def total_monthly_burden(costs: List[RecurringCost]) -> float:
    return round(sum(c.monthly_burden for c in costs), 2)


def suspicious_costs(costs: List[RecurringCost]) -> List[RecurringCost]:
    return [c for c in costs if c.is_suspicious]


def hidden_costs(costs: List[RecurringCost]) -> List[RecurringCost]:
    return [c for c in costs if c.recurring_type == RecurringType.HIDDEN_COST]
