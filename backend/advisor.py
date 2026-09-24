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


# ---------------------------------------------------------------------------
# Main report generation
# ---------------------------------------------------------------------------

async def generate_financial_report(
    metrics     : Dict[str, Any],
    anomalies   : List[Dict],
    recurring   : List[Dict],
    transactions: List[Dict],
    business_type: str,
) -> Dict[str, Any]:
    """
    Generate a full AI financial health report using Mistral.
    Returns a dict compatible with FinancialReport.
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

    raw = _safe_generate(prompt, fallback="{}", json_mode=True)

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        parsed = json.loads(raw)
    except Exception:
        # Fallback: construct a minimal report
        parsed = {
            "executive_summary": raw[:500] if raw else "Analysis complete.",
            "spending_analysis" : "See anomalies and recurring costs for details.",
            "risk_assessment"   : "Review flagged anomalies immediately.",
            "action_items"      : [],
            "cash_flow_forecast": None,
            "risk_items"        : [],
        }

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
