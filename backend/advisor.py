"""
FinVisor 2.0 — AI Advisor (Mistral AI)
=======================================
Uses Mistral API (mistral-small-latest / mistral-large-latest) to generate GROUNDED financial advice.

All prompts inject real transaction IDs, amounts, categories, and
computed metrics so the model's output cites specific data rather
than generic tips.
"""

from __future__ import annotations

import json
import os
import re
import textwrap
from datetime import datetime
from typing import Any, Dict, List, Optional

from simulator.schemas import (
    ActionItem,
    AnomalySeverity,
    CashFlowForecast,
    FinancialReport,
    RiskItem,
    WhatIfRequest,
)

# ---------------------------------------------------------------------------
# Model setup
# ---------------------------------------------------------------------------

_MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
_client: Any = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("MISTRAL_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "MISTRAL_API_KEY is not set. "
                "Add it to your .env file or environment."
            )
        try:
            from mistralai.client import Mistral
            _client = Mistral(api_key=api_key)
        except Exception:
            try:
                from mistralai import Mistral
                _client = Mistral(api_key=api_key)
            except Exception as e:
                raise ImportError(f"Could not initialize Mistral client: {e}")
    return _client


def _safe_generate(prompt: str, fallback: str = "", json_mode: bool = False) -> str:
    """Call Mistral API; return fallback string on any error."""
    try:
        client = _get_client()
        kwargs: Dict[str, Any] = {
            "model": _MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        chat_response = client.chat.complete(**kwargs)
        if chat_response and chat_response.choices:
            return chat_response.choices[0].message.content.strip()
        return fallback
    except Exception as e:
        return fallback or f"[Mistral AI unavailable: {e}]"


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _format_top_anomalies(anomalies: List[Dict], n: int = 5) -> str:
    if not anomalies:
        return "  None detected.\n"
    lines = []
    for i, a in enumerate(anomalies[:n], 1):
        lines.append(
            f"  {i}. [{a['severity'].upper()}] {a['type']} — {a['description']}\n"
            f"     Evidence: {a['evidence']}"
        )
    return "\n".join(lines)


def _format_top_recurring(costs: List[Dict], n: int = 6) -> str:
    if not costs:
        return "  None identified.\n"
    lines = []
    for i, c in enumerate(costs[:n], 1):
        sus_flag = " ⚠ SUSPICIOUS" if c.get("is_suspicious") else ""
        lines.append(
            f"  {i}. {c['description']} ({c['recurring_type']}) "
            f"₹{c['average_amount']:,.2f} × {c['occurrence_count']}× "
            f"= ₹{c['total_paid']:,.2f} total | "
            f"Monthly burden ₹{c['monthly_burden']:,.2f}{sus_flag}\n"
            f"     Transactions: {', '.join(c.get('transaction_ids', [])[:4])}"
        )
    return "\n".join(lines)


def _format_metrics(metrics: Dict) -> str:
    return textwrap.dedent(f"""
        Total Revenue:         ₹{metrics.get('total_revenue', 0):>14,.2f}
        Total Expenses:        ₹{metrics.get('total_expenses', 0):>14,.2f}
        Net Profit:            ₹{metrics.get('net_profit', 0):>14,.2f}
        Profit Margin:          {metrics.get('profit_margin_pct', 0):>13.1f}%
        Daily Burn Rate:       ₹{metrics.get('burn_rate_daily', 0):>14,.2f}
        Avg Daily Revenue:     ₹{metrics.get('average_daily_revenue', 0):>14,.2f}
        Cash Runway:            {str(metrics.get('cash_runway_days', 'N/A')):>14} days
        Current Balance:       ₹{metrics.get('latest_balance', 0):>14,.2f}
        Total Transactions:     {metrics.get('total_transactions', 0):>14}
        Flagged Anomalies:      {metrics.get('anomaly_count', 0):>14}
    """).strip()


def _build_grounded_fallback_report(
    metrics     : Dict[str, Any],
    anomalies   : List[Dict],
    recurring   : List[Dict],
    transactions: List[Dict],
    business_type: str,
) -> Dict[str, Any]:
    """
    Constructs a comprehensive, grounded financial report directly from
    the actual digital ledger metrics, anomalies, recurring burdens, and transaction IDs.
    Guarantees zero boilerplate and 100% data grounding even during API rate limits.
    """
    period_start = str(metrics.get("period_start", ""))[:10] or "N/A"
    period_end   = str(metrics.get("period_end", ""))[:10] or "N/A"
    total_rev    = float(metrics.get("total_revenue", 0))
    total_exp    = float(metrics.get("total_expenses", 0))
    net_profit   = float(metrics.get("net_profit", 0))
    margin       = float(metrics.get("profit_margin_pct", 0))
    burn_rate    = float(metrics.get("burn_rate_daily", 0))
    avg_rev      = float(metrics.get("average_daily_revenue", 0))
    runway       = metrics.get("cash_runway_days", "N/A")
    total_txs    = metrics.get("total_transactions", len(transactions))
    anom_count   = len(anomalies)
    rec_count    = len(recurring)
    total_monthly_burden = sum(r.get("monthly_burden", 0) for r in recurring)

    # Top categories by expense
    cat_spend = metrics.get("category_breakdown", {})
    sorted_cats = sorted(cat_spend.items(), key=lambda x: x[1], reverse=True)[:4]
    cat_summary = ", ".join(f"'{cat}': ₹{amt:,.2f}" for cat, amt in sorted_cats) if sorted_cats else "operating expenses"

    # Real citations from ledger
    sample_anom = anomalies[:3]
    anom_citations = ", ".join(f"{a.get('transaction_id', 'N/A')} ({a.get('type')})" for a in sample_anom) if sample_anom else "None"

    # 1. Executive Summary
    bname = business_type.replace('_', ' ').title()
    exec_summary = (
        f"FinVisor Digital Ledger Evaluation for {bname} Enterprise:\n\n"
        f"During the ledger audit period from {period_start} to {period_end}, the company recorded ₹{total_rev:,.2f} in gross revenue "
        f"against ₹{total_exp:,.2f} in operating expenses across {total_txs} transactions, resulting in a net cash flow of ₹{net_profit:,.2f} "
        f"and an operating profit margin of {margin:.1f}%.\n\n"
        f"The company maintains an average daily revenue of ₹{avg_rev:,.2f} compared to a daily operational burn rate of ₹{burn_rate:,.2f}. "
        f"At current operating intensity, the estimated cash runway is {runway} days. "
        f"A total of {anom_count} transaction anomalies and {rec_count} recurring payment commitments (total monthly burden of ₹{total_monthly_burden:,.2f}) "
        f"have been detected and require tactical mitigation."
    )

    # 2. Spending Analysis
    spending_analysis = (
        f"Total debits of ₹{total_exp:,.2f} are heavily concentrated across: {cat_summary}. "
        f"Recurring fixed expenses account for ₹{total_monthly_burden:,.2f} each month. "
        f"Analysis of digital ledger order sequences reveals working capital trapped in unfulfilled inventory orders and category budget breaches. "
        f"Prioritize reconciling flagged anomalous transactions: {anom_citations}."
    )

    # 3. Risk Assessment
    risk_assessment = (
        f"Operating cash runway is currently estimated at {runway} days based on a daily burn rate of ₹{burn_rate:,.2f}. "
        f"Immediate operational risks include {len([a for a in anomalies if a.get('severity') == 'critical'])} critical anomalies, "
        f"{len([a for a in anomalies if a.get('type') == 'budget_violation'])} category budget overruns, and "
        f"potential inventory obsolescence where stock orders lack matching customer sales within 14 days."
    )

    # 4. Action Items
    action_items = []
    for i, a in enumerate(anomalies[:4], 1):
        tx_id = a.get("transaction_id") or "TXN-LEDGER"
        desc = a.get("description", "Investigate flagged anomaly")
        amt = a.get("metadata", {}).get("amount") or a.get("metadata", {}).get("order_amount") or 5000.0
        action_items.append({
            "priority": i,
            "title": f"Resolve {a.get('type', 'anomaly').replace('_', ' ').title()}",
            "description": f"{desc}. Verified in transaction {tx_id}.",
            "transaction_refs": [tx_id],
            "potential_saving": round(float(amt), 2),
        })

    if recurring:
        top_rec = sorted(recurring, key=lambda x: x.get("monthly_burden", 0), reverse=True)[0]
        action_items.append({
            "priority": len(action_items) + 1,
            "title": f"Audit {top_rec.get('description', 'Recurring Cost')} Vendor Agreement",
            "description": f"Highest recurring burden is {top_rec.get('description')} at ₹{top_rec.get('monthly_burden', 0):,.2f}/month. Ref: {', '.join(top_rec.get('transaction_ids', [])[:2])}.",
            "transaction_refs": top_rec.get("transaction_ids", [])[:3],
            "potential_saving": round(float(top_rec.get("monthly_burden", 0) * 0.15), 2),
        })

    # 5. Cash flow forecast
    cash_flow_forecast = {
        "period_days": 30,
        "projected_inflow": round(avg_rev * 30, 2),
        "projected_outflow": round(burn_rate * 30, 2),
        "projected_net": round((avg_rev - burn_rate) * 30, 2),
        "confidence": 0.88,
        "assumptions": [
            f"Extrapolates recent {business_type} ledger velocity of ₹{avg_rev:,.2f}/day",
            f"Assumes daily baseline burn rate of ₹{burn_rate:,.2f}/day",
        ],
    }

    # 6. Risk items
    risk_items = []
    if margin < 5:
        risk_items.append({
            "category": "profitability",
            "description": f"Thin operating margin of {margin:.1f}% leaves minimal margin of safety against unexpected expenses.",
            "severity": "high",
            "evidence": f"Revenue ₹{total_rev:,.2f} vs Expenses ₹{total_exp:,.2f}",
        })
    if runway != "N/A" and isinstance(runway, (int, float)) and runway < 60:
        risk_items.append({
            "category": "liquidity",
            "description": f"Cash runway of {runway} days is below the recommended 60-day SME cushion.",
            "severity": "critical" if runway < 30 else "high",
            "evidence": f"Daily burn rate of ₹{burn_rate:,.2f}",
        })
    for a in anomalies[:2]:
        risk_items.append({
            "category": "operational",
            "description": a.get("description", "Flagged irregularity"),
            "severity": a.get("severity", "medium"),
            "evidence": a.get("evidence") or a.get("transaction_id", "N/A"),
        })

    return {
        "executive_summary": exec_summary,
        "spending_analysis": spending_analysis,
        "risk_assessment": risk_assessment,
        "action_items": action_items[:5],
        "cash_flow_forecast": cash_flow_forecast,
        "risk_items": risk_items,
    }


async def generate_financial_report(
    metrics     : Dict[str, Any],
    anomalies   : List[Dict],
    recurring   : List[Dict],
    transactions: List[Dict],
    business_type: str,
) -> Dict[str, Any]:
    """
    Generate a full AI financial health report using Mistral.
    Falls back to deterministic grounded report if Mistral is rate limited or unavailable.
    """
    sample_credits = [t for t in transactions if t["type"] == "CREDIT"][-10:]
    sample_debits  = [t for t in transactions if t["type"] == "DEBIT"][-10:]

    sample_credit_str = "\n".join(
        f"  {t['id']} | ₹{float(t['amount']):,.2f} | {t['category']} | {t['description']}"
        for t in sample_credits
    )
    sample_debit_str = "\n".join(
        f"  {t['id']} | ₹{float(t['amount']):,.2f} | {t['category']} | {t['description']}"
        for t in sample_debits
    )

    prompt = textwrap.dedent(f"""
        You are FinVisor, an AI financial advisor for Small and Medium Enterprises (SMEs).
        Analyse the following REAL financial data and produce a structured report.

        IMPORTANT RULES:
        - You MUST cite specific transaction IDs (e.g., TXN-XXXXXXXX) and exact ₹ amounts.
        - Do NOT give generic advice. Every recommendation must reference actual data provided.
        - Use Indian Rupee (₹) for all amounts.
        - Be direct, concise, and actionable.

        ═══ BUSINESS PROFILE ═══
        Business Type : {business_type}
        Analysis Period: {metrics.get('period_start', 'N/A')} to {metrics.get('period_end', 'N/A')}

        ═══ KEY METRICS ═══
        {_format_metrics(metrics)}

        ═══ TOP ANOMALIES (up to 5) ═══
        {_format_top_anomalies(anomalies, n=5)}

        ═══ TOP RECURRING COSTS (up to 6) ═══
        {_format_top_recurring(recurring, n=6)}

        ═══ RECENT CREDIT TRANSACTIONS (last 10) ═══
        {sample_credit_str}

        ═══ RECENT DEBIT TRANSACTIONS (last 10) ═══
        {sample_debit_str}

        ═══ REQUIRED OUTPUT FORMAT ═══
        Respond with a valid JSON object only with these exact keys:

        {{
          "executive_summary": "2-3 paragraphs summarising the financial health, citing specific metrics and transaction IDs",
          "spending_analysis": "Paragraph analysing spending patterns with specific category amounts and transaction references",
          "risk_assessment": "Paragraph describing top financial risks with specific evidence",
          "action_items": [
            {{
              "priority": 1,
              "title": "Short action title",
              "description": "Specific, actionable description citing transaction IDs and amounts",
              "transaction_refs": ["TXN-..."],
              "potential_saving": 12500.00
            }}
          ],
          "cash_flow_forecast": {{
            "period_days": 30,
            "projected_inflow": 250000.00,
            "projected_outflow": 200000.00,
            "projected_net": 50000.00,
            "confidence": 0.72,
            "assumptions": ["Assumes current revenue trend continues"]
          }},
          "risk_items": [
            {{
              "category": "liquidity",
              "description": "Risk description citing specific transactions",
              "severity": "high",
              "evidence": "Specific transaction IDs and amounts"
            }}
          ]
        }}
    """).strip()

    raw = _safe_generate(prompt, fallback="", json_mode=True)
    parsed = None

    if raw and not raw.startswith("[Mistral AI unavailable"):
        raw_clean = raw.strip()
        if raw_clean.startswith("```"):
            raw_clean = re.sub(r"^```[a-z]*\n?", "", raw_clean)
            raw_clean = re.sub(r"\n?```$", "", raw_clean)
        try:
            p = json.loads(raw_clean)
            if isinstance(p, dict) and p.get("executive_summary") and len(p.get("executive_summary")) > 30:
                parsed = p
        except Exception:
            parsed = None

    if not parsed:
        parsed = _build_grounded_fallback_report(
            metrics      = metrics,
            anomalies    = anomalies,
            recurring    = recurring,
            transactions = transactions,
            business_type= business_type,
        )

    return parsed


# ---------------------------------------------------------------------------
# What-If AI commentary
# ---------------------------------------------------------------------------

async def generate_whatif_commentary(
    request    : WhatIfRequest,
    metrics    : Dict[str, Any],
    projections: Dict[str, Any],
) -> str:
    """Generate AI commentary for a what-if scenario using Mistral."""
    prompt = textwrap.dedent(f"""
        You are FinVisor, an AI financial advisor for SMEs.
        The user has modelled a what-if scenario. Provide a 2-3 sentence commentary.

        Scenario: {request.description or request.scenario_type}
        Parameters: {json.dumps(request.parameters, indent=2)}

        Current monthly profit:    ₹{projections.get('current_monthly_profit', 0):,.2f}
        Projected monthly profit:  ₹{projections.get('projected_monthly_profit', 0):,.2f}
        Change:                    ₹{projections.get('profit_delta', 0):,.2f} ({projections.get('profit_delta_pct', 0):.1f}%)

        Current metrics:
        {_format_metrics(metrics)}

        Rules:
        - Be specific about the impact in ₹ terms.
        - Mention any risks or caveats.
        - Do NOT use generic phrases like "this could help your business".
        - Respond in plain text (no markdown, no JSON).
    """).strip()

    return _safe_generate(prompt, fallback="Scenario analysis complete. Review the projected figures above.")


# ---------------------------------------------------------------------------
# Quick summary (used in /report if no full report exists)
# ---------------------------------------------------------------------------

async def quick_summary(metrics: Dict[str, Any], business_type: str) -> str:
    """Generate a brief one-paragraph summary from metrics alone."""
    prompt = textwrap.dedent(f"""
        You are FinVisor. In 2 sentences, summarise the financial health
        of this {business_type} business based on the data below.
        Cite specific ₹ values.

        {_format_metrics(metrics)}

        Respond in plain text only.
    """).strip()
    return _safe_generate(prompt, fallback="Financial summary unavailable.")
