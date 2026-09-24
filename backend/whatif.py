"""
FinVisor 2.0 — What-If Scenario Simulator
==========================================
Simulates hypothetical financial scenarios and projects their impact
on cash flow and profitability.

Supported scenario types
------------------------
  reduce_category       — Reduce spending in a category by X%
  increase_sales        — Increase overall revenue by X%
  eliminate_subscription— Remove a specific subscription cost
  add_revenue_stream    — Add a new monthly revenue source
  reduce_burn_rate      — Reduce overall daily expenses by X%
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from simulator.schemas import WhatIfRequest, WhatIfResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _monthly(daily: float) -> float:
    return round(daily * 30, 2)


def _delta_pct(old: float, new: float) -> float:
    if old == 0:
        return 0.0
    return round((new - old) / abs(old) * 100, 2)


# ---------------------------------------------------------------------------
# Scenario handlers
# ---------------------------------------------------------------------------

def _reduce_category(
    params       : Dict[str, Any],
    metrics      : Dict[str, Any],
    raw_txs      : List[Dict],
) -> Dict[str, Any]:
    """
    Reduce spending in `category` by `reduction_pct` percent.
    params: {category: str, reduction_pct: float (0-100)}
    """
    category      = params.get("category", "")
    reduction_pct = float(params.get("reduction_pct", 10)) / 100

    df = pd.DataFrame(raw_txs)
    df["amount"] = df["amount"].astype(float)
    debits = df[df["type"] == "DEBIT"]

    cat_total = float(debits[debits["category"] == category]["amount"].sum()) if category else 0
    n_days    = metrics.get("n_days", 30)

    saving_total   = cat_total * reduction_pct
    saving_monthly = round(saving_total / n_days * 30, 2) if n_days > 0 else 0

    cur_monthly_expenses    = _monthly(metrics.get("burn_rate_daily", 0))
    proj_monthly_expenses   = round(cur_monthly_expenses - saving_monthly, 2)
    cur_monthly_revenue     = _monthly(metrics.get("average_daily_revenue", 0))
    proj_monthly_revenue    = cur_monthly_revenue   # unchanged
    cur_monthly_profit      = round(cur_monthly_revenue  - cur_monthly_expenses,  2)
    proj_monthly_profit     = round(proj_monthly_revenue - proj_monthly_expenses, 2)

    return {
        "saving_monthly"        : saving_monthly,
        "current_monthly_expenses"  : cur_monthly_expenses,
        "projected_monthly_expenses": proj_monthly_expenses,
        "current_monthly_revenue"   : cur_monthly_revenue,
        "projected_monthly_revenue" : proj_monthly_revenue,
        "current_monthly_profit"    : cur_monthly_profit,
        "projected_monthly_profit"  : proj_monthly_profit,
        "assumptions"           : [
            f"Category '{category}' spending reduced by {reduction_pct*100:.0f}%",
            "All other costs remain constant",
            "Revenue unaffected by this cost reduction",
        ],
    }


def _increase_sales(
    params       : Dict[str, Any],
    metrics      : Dict[str, Any],
    raw_txs      : List[Dict],
) -> Dict[str, Any]:
    """
    Increase overall revenue by `increase_pct` percent.
    params: {increase_pct: float}
    """
    increase_pct = float(params.get("increase_pct", 10)) / 100

    cur_monthly_revenue     = _monthly(metrics.get("average_daily_revenue", 0))
    cur_monthly_expenses    = _monthly(metrics.get("burn_rate_daily", 0))
    proj_monthly_revenue    = round(cur_monthly_revenue * (1 + increase_pct), 2)
    proj_monthly_expenses   = cur_monthly_expenses   # assuming marginal cost is negligible
    cur_monthly_profit      = round(cur_monthly_revenue  - cur_monthly_expenses,  2)
    proj_monthly_profit     = round(proj_monthly_revenue - proj_monthly_expenses, 2)

    return {
        "current_monthly_expenses"  : cur_monthly_expenses,
        "projected_monthly_expenses": proj_monthly_expenses,
        "current_monthly_revenue"   : cur_monthly_revenue,
        "projected_monthly_revenue" : proj_monthly_revenue,
        "current_monthly_profit"    : cur_monthly_profit,
        "projected_monthly_profit"  : proj_monthly_profit,
        "assumptions"               : [
            f"Revenue increases by {increase_pct*100:.0f}% uniformly",
            "Cost of goods sold proportional increase not modelled",
            "Fixed costs remain unchanged",
        ],
    }


def _eliminate_subscription(
    params       : Dict[str, Any],
    metrics      : Dict[str, Any],
    raw_txs      : List[Dict],
) -> Dict[str, Any]:
    """
    Remove a specific subscription identified by keyword in description.
    params: {keyword: str}  — e.g. {"keyword": "Salesforce"}
    """
    keyword = params.get("keyword", "").lower()

    df = pd.DataFrame(raw_txs)
    df["amount"] = df["amount"].astype(float)
    debits = df[df["type"] == "DEBIT"]
    subs   = debits[
        debits["description"].str.lower().str.contains(keyword, na=False) &
        (debits["category"] == "subscriptions")
    ]

    n_days       = metrics.get("n_days", 30)
    sub_total    = float(subs["amount"].sum())
    saving_monthly = round(sub_total / n_days * 30, 2) if n_days > 0 else 0

    cur_monthly_expenses    = _monthly(metrics.get("burn_rate_daily", 0))
    proj_monthly_expenses   = round(cur_monthly_expenses - saving_monthly, 2)
    cur_monthly_revenue     = _monthly(metrics.get("average_daily_revenue", 0))
    cur_monthly_profit      = round(cur_monthly_revenue - cur_monthly_expenses,  2)
    proj_monthly_profit     = round(cur_monthly_revenue - proj_monthly_expenses, 2)

    return {
        "subscription_found"        : not subs.empty,
        "matched_transactions"      : len(subs),
        "total_paid"                : sub_total,
        "saving_monthly"            : saving_monthly,
        "current_monthly_expenses"  : cur_monthly_expenses,
        "projected_monthly_expenses": proj_monthly_expenses,
        "current_monthly_revenue"   : cur_monthly_revenue,
        "projected_monthly_revenue" : cur_monthly_revenue,
        "current_monthly_profit"    : cur_monthly_profit,
        "projected_monthly_profit"  : proj_monthly_profit,
        "assumptions"               : [
            f"All transactions matching '{keyword}' in subscriptions are eliminated",
            "No replacement service cost assumed",
            "Productivity impact not modelled",
        ],
    }


def _add_revenue_stream(
    params       : Dict[str, Any],
    metrics      : Dict[str, Any],
    raw_txs      : List[Dict],
) -> Dict[str, Any]:
    """
    Add a new monthly revenue stream.
    params: {monthly_amount: float, stream_name: str}
    """
    monthly_amount = float(params.get("monthly_amount", 0))
    stream_name    = params.get("stream_name", "New Revenue Stream")

    cur_monthly_revenue   = _monthly(metrics.get("average_daily_revenue", 0))
    cur_monthly_expenses  = _monthly(metrics.get("burn_rate_daily", 0))
    proj_monthly_revenue  = round(cur_monthly_revenue + monthly_amount, 2)
    proj_monthly_expenses = cur_monthly_expenses
    cur_monthly_profit    = round(cur_monthly_revenue  - cur_monthly_expenses,  2)
    proj_monthly_profit   = round(proj_monthly_revenue - proj_monthly_expenses, 2)

    return {
        "current_monthly_expenses"  : cur_monthly_expenses,
        "projected_monthly_expenses": proj_monthly_expenses,
        "current_monthly_revenue"   : cur_monthly_revenue,
        "projected_monthly_revenue" : proj_monthly_revenue,
        "current_monthly_profit"    : cur_monthly_profit,
        "projected_monthly_profit"  : proj_monthly_profit,
        "assumptions"               : [
            f"'{stream_name}' generates a stable ₹{monthly_amount:,.2f}/month",
            "No additional costs associated with this stream",
            "Stream begins immediately",
        ],
    }


def _reduce_burn_rate(
    params       : Dict[str, Any],
    metrics      : Dict[str, Any],
    raw_txs      : List[Dict],
) -> Dict[str, Any]:
    """
    Reduce overall daily expense (burn rate) by X%.
    params: {reduction_pct: float}
    """
    reduction_pct = float(params.get("reduction_pct", 10)) / 100

    cur_monthly_expenses    = _monthly(metrics.get("burn_rate_daily", 0))
    proj_monthly_expenses   = round(cur_monthly_expenses * (1 - reduction_pct), 2)
    cur_monthly_revenue     = _monthly(metrics.get("average_daily_revenue", 0))
    cur_monthly_profit      = round(cur_monthly_revenue - cur_monthly_expenses,  2)
    proj_monthly_profit     = round(cur_monthly_revenue - proj_monthly_expenses, 2)

    return {
        "current_monthly_expenses"  : cur_monthly_expenses,
        "projected_monthly_expenses": proj_monthly_expenses,
        "current_monthly_revenue"   : cur_monthly_revenue,
        "projected_monthly_revenue" : cur_monthly_revenue,
        "current_monthly_profit"    : cur_monthly_profit,
        "projected_monthly_profit"  : proj_monthly_profit,
        "assumptions"               : [
            f"All variable expenses reduced by {reduction_pct*100:.0f}% uniformly",
            "Fixed costs (rent, salaries) not reducible in this model",
            "Revenue unaffected",
        ],
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_HANDLERS = {
    "reduce_category"        : _reduce_category,
    "increase_sales"         : _increase_sales,
    "eliminate_subscription" : _eliminate_subscription,
    "add_revenue_stream"     : _add_revenue_stream,
    "reduce_burn_rate"       : _reduce_burn_rate,
}


async def run_whatif(
    request  : WhatIfRequest,
    metrics  : Dict[str, Any],
    raw_txs  : List[Dict],
) -> WhatIfResult:
    """
    Run a what-if scenario simulation.
    Returns a WhatIfResult with projections and AI commentary.
    """
    handler = _HANDLERS.get(request.scenario_type)
    if handler is None:
        raise ValueError(
            f"Unknown scenario_type '{request.scenario_type}'. "
            f"Valid types: {list(_HANDLERS.keys())}"
        )

    projections = handler(request.parameters, metrics, raw_txs)

    cur_profit  = projections.get("current_monthly_profit", 0)
    proj_profit = projections.get("projected_monthly_profit", 0)
    delta       = round(proj_profit - cur_profit, 2)
    delta_pct   = _delta_pct(cur_profit, proj_profit)

    # AI commentary
    from backend.advisor import generate_whatif_commentary
    commentary = await generate_whatif_commentary(
        request     = request,
        metrics     = metrics,
        projections = projections,
    )

    return WhatIfResult(
        id                          = f"WIF-{uuid.uuid4().hex[:10].upper()}",
        request                     = request,
        created_at                  = datetime.utcnow(),
        current_monthly_profit      = cur_profit,
        projected_monthly_profit    = proj_profit,
        profit_delta                = delta,
        profit_delta_pct            = delta_pct,
        current_monthly_expenses    = projections.get("current_monthly_expenses", 0),
        projected_monthly_expenses  = projections.get("projected_monthly_expenses", 0),
        current_monthly_revenue     = projections.get("current_monthly_revenue", 0),
        projected_monthly_revenue   = projections.get("projected_monthly_revenue", 0),
        ai_commentary               = commentary,
        assumptions                 = projections.get("assumptions", []),
        confidence                  = 0.75,
    )
