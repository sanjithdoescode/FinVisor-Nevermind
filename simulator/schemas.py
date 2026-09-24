"""
Pydantic schemas / data models for FinVisor 2.0.

These models are shared between the simulator, backend API, and
analysis pipeline to ensure a single source of truth for data shapes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TransactionType(str, Enum):
    CREDIT = "CREDIT"   # money in  (sales, refunds received, loans)
    DEBIT  = "DEBIT"    # money out (expenses, orders, payments)


class BusinessType(str, Enum):
    RETAILER         = "retailer"
    RESTAURANT       = "restaurant"
    SERVICE_PROVIDER = "service_provider"


class AnomalySeverity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    STATISTICAL_OUTLIER  = "statistical_outlier"
    DUPLICATE_PAYMENT    = "duplicate_payment"
    UNUSUAL_TIMING       = "unusual_timing"
    BUDGET_VIOLATION     = "budget_violation"
    IDLE_INVENTORY       = "idle_inventory"
    IRREGULAR_INCOME     = "irregular_income"


class RecurringType(str, Enum):
    SUBSCRIPTION = "subscription"
    RECURRING    = "recurring"
    HIDDEN_COST  = "hidden_cost"


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class Transaction(BaseModel):
    """Core financial transaction record."""

    id              : str
    timestamp       : datetime
    amount          : float = Field(..., ge=0)
    type            : TransactionType
    category        : str
    description     : str
    account_balance : float
    business_type   : BusinessType
    tags            : List[str] = Field(default_factory=list)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("account_balance")
    @classmethod
    def round_balance(cls, v: float) -> float:
        return round(v, 2)

    def to_redis_dict(self) -> Dict[str, str]:
        """Serialize to flat string dict suitable for Redis XADD."""
        return {
            "id"              : self.id,
            "timestamp"       : self.timestamp.isoformat(),
            "amount"          : str(self.amount),
            "type"            : self.type.value,
            "category"        : self.category,
            "description"     : self.description,
            "account_balance" : str(self.account_balance),
            "business_type"   : self.business_type.value,
            "tags"            : ",".join(self.tags),
        }

    @classmethod
    def from_redis_dict(cls, data: Dict[str, str]) -> "Transaction":
        """Deserialize from Redis XREAD entry."""
        return cls(
            id              = data["id"],
            timestamp       = datetime.fromisoformat(data["timestamp"]),
            amount          = float(data["amount"]),
            type            = TransactionType(data["type"]),
            category        = data["category"],
            description     = data["description"],
            account_balance = float(data["account_balance"]),
            business_type   = BusinessType(data["business_type"]),
            tags            = [t for t in data.get("tags", "").split(",") if t],
        )


# ---------------------------------------------------------------------------
# Anomaly
# ---------------------------------------------------------------------------

class Anomaly(BaseModel):
    """A detected anomaly referencing one or more transactions."""

    id             : str
    transaction_id : str
    type           : AnomalyType
    severity       : AnomalySeverity
    description    : str
    evidence       : str          # human-readable, cites specific tx IDs/amounts
    detected_at    : datetime = Field(default_factory=datetime.utcnow)
    metadata       : Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Recurring Cost
# ---------------------------------------------------------------------------

class RecurringCost(BaseModel):
    """A recurring or hidden cost pattern identified from transactions."""

    id                    : str
    category              : str
    description           : str
    merchant              : Optional[str] = None
    recurring_type        : RecurringType
    frequency_days        : Optional[float] = None   # average days between occurrences
    average_amount        : float
    total_paid            : float
    occurrence_count      : int
    transaction_ids       : List[str]
    is_necessary          : bool = True
    is_suspicious         : bool = False
    monthly_burden        : float = 0.0              # normalised to 30-day period
    first_seen            : datetime
    last_seen             : datetime
    notes                 : str = ""


# ---------------------------------------------------------------------------
# Financial Health Report
# ---------------------------------------------------------------------------

class CashFlowForecast(BaseModel):
    period_days       : int
    projected_inflow  : float
    projected_outflow : float
    projected_net     : float
    confidence        : float = Field(..., ge=0.0, le=1.0)
    assumptions       : List[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    category    : str
    description : str
    severity    : AnomalySeverity
    evidence    : str


class ActionItem(BaseModel):
    priority         : int          # 1 = highest
    title            : str
    description      : str
    transaction_refs : List[str]    # specific tx IDs
    potential_saving : Optional[float] = None


class FinancialReport(BaseModel):
    """Full financial health report generated by the AI advisor."""

    id                    : str
    generated_at          : datetime = Field(default_factory=datetime.utcnow)
    business_type         : BusinessType
    period_start          : datetime
    period_end            : datetime

    # Metrics
    total_revenue         : float
    total_expenses        : float
    net_profit            : float
    profit_margin_pct     : float
    burn_rate_daily       : float
    average_daily_revenue : float
    cash_runway_days      : Optional[float] = None

    # Counts
    total_transactions    : int
    anomaly_count         : int
    recurring_cost_count  : int

    # Narrative (AI-generated)
    executive_summary     : str
    spending_analysis     : str
    risk_assessment       : str

    # Structured items
    action_items          : List[ActionItem] = Field(default_factory=list)
    cash_flow_forecast    : Optional[CashFlowForecast] = None
    risk_items            : List[RiskItem] = Field(default_factory=list)

    # Raw AI output (full markdown)
    full_report_markdown  : str = ""


# ---------------------------------------------------------------------------
# What-If Scenario
# ---------------------------------------------------------------------------

class WhatIfRequest(BaseModel):
    scenario_type : str   # "reduce_category", "increase_sales", "eliminate_subscription"
    parameters    : Dict[str, Any]
    description   : str = ""


class WhatIfResult(BaseModel):
    id                     : str
    request                : WhatIfRequest
    created_at             : datetime = Field(default_factory=datetime.utcnow)

    current_monthly_profit : float
    projected_monthly_profit: float
    profit_delta           : float
    profit_delta_pct       : float

    current_monthly_expenses: float
    projected_monthly_expenses: float

    current_monthly_revenue : float
    projected_monthly_revenue: float

    ai_commentary          : str
    assumptions            : List[str] = Field(default_factory=list)
    confidence             : float = Field(default=0.75, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# API response wrappers
# ---------------------------------------------------------------------------

class PaginatedTransactions(BaseModel):
    items      : List[Transaction]
    total      : int
    page       : int
    page_size  : int
    has_more   : bool


class HealthCheck(BaseModel):
    status       : str
    redis        : str
    database     : str
    timestamp    : datetime = Field(default_factory=datetime.utcnow)
    version      : str = "2.0.0"
