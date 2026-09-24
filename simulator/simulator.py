"""
FinVisor 2.0 — Transaction Simulator
=====================================
Generates realistic SME transaction data and publishes it to:
  • Redis stream  →  transactions:live
  • SQLite DB     →  transactions table

Usage
-----
  python simulator/simulator.py --mode batch [--count 1000] [--business retailer]
  python simulator/simulator.py --mode live  [--interval 2]  [--business restaurant]

Business types: retailer | restaurant | service_provider
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import redis

# ---------------------------------------------------------------------------
# Make simulator importable from project root too
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from simulator.schemas import BusinessType, Transaction, TransactionType

# ---------------------------------------------------------------------------
# Business Profile Definitions
# ---------------------------------------------------------------------------

BUSINESS_PROFILES: Dict[str, Dict] = {
    "retailer": {
        "credit_categories": ["product_sales", "online_sales", "returns_received", "bulk_order"],
        "debit_categories":  ["inventory_purchase", "rent", "utilities", "salaries", "marketing",
                               "logistics", "pos_fees", "subscriptions", "maintenance", "insurance"],
        "avg_daily_revenue":  8_500,
        "revenue_variance":   0.40,
        "avg_tx_amount":      420,
        "business_hours":     (8, 21),
        "peak_days":          [4, 5, 6],   # Fri, Sat, Sun
        "peak_multiplier":    1.6,
        "monthly_fixed": [
            ("rent",          45_000, 1),
            ("salaries",      120_000, 28),
            ("insurance",     3_500, 15),
            ("pos_fees",      1_800, 5),
        ],
        "subscriptions": [
            ("Shopify",       2_999, 1),
            ("QuickBooks",    1_499, 10),
            ("Slack",         799, 20),
            ("Google Workspace", 1_200, 25),
        ],
    },
    "restaurant": {
        "credit_categories": ["dine_in", "takeaway", "delivery_platform", "catering", "event_booking"],
        "debit_categories":  ["raw_materials", "rent", "utilities", "salaries", "marketing",
                               "kitchen_equipment", "pos_fees", "subscriptions", "delivery_fees",
                               "waste_disposal", "health_inspection"],
        "avg_daily_revenue":  14_000,
        "revenue_variance":   0.55,
        "avg_tx_amount":      680,
        "business_hours":     (11, 23),
        "peak_days":          [4, 5, 6],
        "peak_multiplier":    1.8,
        "monthly_fixed": [
            ("rent",          80_000, 1),
            ("salaries",      200_000, 28),
            ("insurance",     5_000, 15),
            ("pos_fees",      2_200, 5),
        ],
        "subscriptions": [
            ("Zomato Pro",    4_999, 1),
            ("Swiggy Partner",3_999, 1),
            ("PetPooja POS",  1_999, 10),
            ("HubSpot",       2_499, 20),
        ],
    },
    "service_provider": {
        "credit_categories": ["consulting_fee", "project_payment", "retainer", "subscription_revenue",
                               "training_fee", "license_fee"],
        "debit_categories":  ["salaries", "rent", "utilities", "software_licenses", "marketing",
                               "travel", "subscriptions", "legal_fees", "cloud_services",
                               "training", "office_supplies"],
        "avg_daily_revenue":  22_000,
        "revenue_variance":   0.70,   # feast/famine prominent
        "avg_tx_amount":      3_500,
        "business_hours":     (9, 19),
        "peak_days":          [0, 1, 2, 3, 4],  # weekdays only
        "peak_multiplier":    1.3,
        "monthly_fixed": [
            ("rent",          60_000, 1),
            ("salaries",      350_000, 28),
            ("insurance",     4_000, 15),
        ],
        "subscriptions": [
            ("AWS",           8_500, 1),
            ("GitHub",        1_999, 5),
            ("Jira",          2_499, 10),
            ("Zoom",          1_299, 15),
            ("Salesforce",    12_999, 20),
            ("Slack",         1_799, 25),
        ],
    },
}

# Category descriptions for realistic narrations
DESCRIPTIONS: Dict[str, List[str]] = {
    # Credits
    "product_sales"        : ["In-store sales", "POS transaction", "Counter sale", "Walk-in customer"],
    "online_sales"         : ["Shopify order", "Amazon marketplace", "Website checkout", "Online cart"],
    "bulk_order"           : ["Bulk purchase - B2B", "Wholesale order", "Corporate purchase"],
    "returns_received"     : ["Supplier credit note", "Return from vendor"],
    "dine_in"              : ["Table service", "Dine-in bill", "Restaurant table", "Buffet service"],
    "takeaway"             : ["Takeaway order", "Counter pickup", "Phone order"],
    "delivery_platform"    : ["Zomato delivery", "Swiggy order", "Uber Eats"],
    "catering"             : ["Catering event", "Office catering", "Wedding catering"],
    "event_booking"        : ["Private event booking", "Birthday party booking"],
    "consulting_fee"       : ["Strategy consulting", "Advisory fee", "Consulting invoice"],
    "project_payment"      : ["Project milestone payment", "Project completion", "Development invoice"],
    "retainer"             : ["Monthly retainer", "Retainer fee", "Ongoing retainer"],
    "subscription_revenue" : ["SaaS subscription", "Platform subscription", "Annual subscription"],
    "training_fee"         : ["Training workshop", "Certification program"],
    "license_fee"          : ["Software license", "IP license fee"],
    # Debits
    "inventory_purchase"   : ["Stock replenishment", "Inventory order", "Supplier payment"],
    "raw_materials"        : ["Vegetable purchase", "Meat supplier", "Dairy delivery", "Grain purchase"],
    "rent"                 : ["Monthly rent", "Office rent", "Store rent"],
    "utilities"            : ["Electricity bill", "Water bill", "Gas bill", "Internet bill"],
    "salaries"             : ["Monthly salary disbursement", "Staff payroll", "Contractor payment"],
    "marketing"            : ["Facebook Ads", "Google Ads", "Influencer payment", "Print marketing"],
    "logistics"            : ["Courier charges", "Shipping cost", "Last-mile delivery"],
    "pos_fees"             : ["POS terminal fee", "Payment gateway fee", "Razorpay settlement"],
    "subscriptions"        : ["Software subscription", "SaaS renewal", "Annual license"],
    "maintenance"          : ["Equipment maintenance", "AC servicing", "Plumbing repair"],
    "insurance"            : ["Business insurance premium", "Fire insurance", "General insurance"],
    "software_licenses"    : ["Software license renewal", "Enterprise license"],
    "travel"               : ["Client visit travel", "Conference travel", "Taxi/Uber"],
    "legal_fees"           : ["Legal consultation", "Contract review", "IP filing"],
    "cloud_services"       : ["AWS invoice", "GCP billing", "Azure subscription"],
    "training"             : ["Team training", "Upskilling program", "Conference registration"],
    "office_supplies"      : ["Stationery", "Printer cartridge", "Office supplies"],
    "kitchen_equipment"    : ["Equipment repair", "Commercial oven part", "Refrigeration service"],
    "delivery_fees"        : ["Delivery platform commission", "Delivery driver payout"],
    "waste_disposal"       : ["Waste management", "Garbage collection fee"],
    "health_inspection"    : ["Health dept inspection fee", "Fire safety certificate"],
}


# ---------------------------------------------------------------------------
# Simulator Core
# ---------------------------------------------------------------------------

class SMESimulator:
    """Generates realistic SME transaction sequences."""

    STREAM_KEY = "transactions:live"

    def __init__(
        self,
        business_type: str = "retailer",
        db_path: str = "finvisor.db",
        redis_url: str = "redis://localhost:6379",
        start_date: Optional[datetime] = None,
        anomaly_rate: float = 0.04,    # ~4% of transactions are anomalous
        hidden_cost_rate: float = 0.03,
    ):
        self.business_type  = BusinessType(business_type)
        self.profile        = BUSINESS_PROFILES[business_type]
        self.db_path        = db_path
        self.anomaly_rate   = anomaly_rate
        self.hidden_cost_rate = hidden_cost_rate
        self.start_date     = start_date or (datetime.utcnow() - timedelta(days=180))
        self.account_balance: float = random.uniform(200_000, 500_000)
        self._pending_orders: List[Dict] = []   # track orders w/o matching sales

        # Connect to Redis
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            self._redis_ok = True
        except Exception as e:
            print(f"[WARN] Redis unavailable ({e}). Transactions will only go to SQLite.")
            self.redis = None  # type: ignore
            self._redis_ok = False

        # Set up SQLite
        self._init_db()

    # ------------------------------------------------------------------
    # DB setup
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create transactions table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
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
            )
        """)
        conn.commit()
        conn.close()

    def _insert_db(self, tx: Transaction) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR IGNORE INTO transactions
            (id, timestamp, amount, type, category, description, account_balance, business_type, tags)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            tx.id, tx.timestamp.isoformat(), tx.amount, tx.type.value,
            tx.category, tx.description, tx.account_balance,
            tx.business_type.value, ",".join(tx.tags)
        ))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Redis publish
    # ------------------------------------------------------------------

    def _publish_redis(self, tx: Transaction) -> None:
        if self.redis is None:
            return
        try:
            self.redis.xadd(self.STREAM_KEY, tx.to_redis_dict(), maxlen=5000)
        except Exception as e:
            print(f"[WARN] Redis XADD failed: {e}")

    # ------------------------------------------------------------------
    # Transaction builders
    # ------------------------------------------------------------------

    def _make_id(self) -> str:
        return f"TXN-{uuid.uuid4().hex[:12].upper()}"

    def _pick_desc(self, category: str) -> str:
        options = DESCRIPTIONS.get(category, [category.replace("_", " ").title()])
        return random.choice(options)

    def _credit(
        self,
        timestamp: datetime,
        category: str,
        amount: float,
        tags: Optional[List[str]] = None,
        desc: Optional[str] = None,
    ) -> Transaction:
        self.account_balance = round(self.account_balance + amount, 2)
        return Transaction(
            id              = self._make_id(),
            timestamp       = timestamp,
            amount          = round(amount, 2),
            type            = TransactionType.CREDIT,
            category        = category,
            description     = desc or self._pick_desc(category),
            account_balance = self.account_balance,
            business_type   = self.business_type,
            tags            = tags or [],
        )

    def _debit(
        self,
        timestamp: datetime,
        category: str,
        amount: float,
        tags: Optional[List[str]] = None,
        desc: Optional[str] = None,
    ) -> Transaction:
        self.account_balance = round(self.account_balance - amount, 2)
        return Transaction(
            id              = self._make_id(),
            timestamp       = timestamp,
            amount          = round(amount, 2),
            type            = TransactionType.DEBIT,
            category        = category,
            description     = desc or self._pick_desc(category),
            account_balance = self.account_balance,
            business_type   = self.business_type,
            tags            = tags or [],
        )

    # ------------------------------------------------------------------
    # Monthly fixed costs (rent, salaries, subscriptions)
    # ------------------------------------------------------------------

    def _monthly_fixed(self, year: int, month: int) -> List[Transaction]:
        txs: List[Transaction] = []
        for cat, base_amount, day in self.profile["monthly_fixed"]:
            try:
                ts = datetime(year, month, day,
                              random.randint(9, 11), random.randint(0, 59))
            except ValueError:
                continue  # e.g. Feb 30
            variance = random.uniform(-0.02, 0.02)
            amount   = base_amount * (1 + variance)
            tx = self._debit(ts, cat, amount, tags=["recurring", "fixed_cost"],
                             desc=f"{cat.replace('_',' ').title()} - {ts.strftime('%b %Y')}")
            txs.append(tx)

        for name, base_amount, day in self.profile["subscriptions"]:
            try:
                ts = datetime(year, month, day,
                              random.randint(0, 6), random.randint(0, 59))
            except ValueError:
                continue
            # Occasionally introduce a hidden duplicate subscription
            is_hidden   = random.random() < 0.05
            amount      = base_amount
            tags        = ["subscription", "recurring"]
            if is_hidden:
                tags.append("hidden_cost")
            tx = self._debit(ts, "subscriptions", amount, tags=tags,
                             desc=f"{name} subscription")
            txs.append(tx)
            if is_hidden:
                # Duplicate charge same day
                dup_ts = ts + timedelta(hours=random.randint(1, 5))
                dup_tx = self._debit(dup_ts, "subscriptions", amount,
                                     tags=["subscription", "duplicate", "hidden_cost"],
                                     desc=f"{name} subscription (duplicate charge)")
                txs.append(dup_tx)
        return txs

    # ------------------------------------------------------------------
    # Daily revenue transactions
    # ------------------------------------------------------------------

    def _daily_revenue(self, date: datetime) -> List[Transaction]:
        profile   = self.profile
        h_start, h_end = profile["business_hours"]
        txs: List[Transaction] = []

        is_peak      = date.weekday() in profile["peak_days"]
        multiplier   = profile["peak_multiplier"] if is_peak else 1.0
        day_revenue  = profile["avg_daily_revenue"] * multiplier
        variance     = random.gauss(1.0, profile["revenue_variance"])
        variance     = max(0.05, min(variance, 3.5))  # clamp

        # Feast/famine: occasionally near-zero revenue days
        if random.random() < 0.06:
            variance *= 0.05

        target_revenue = day_revenue * variance
        n_txs          = max(1, int(target_revenue / profile["avg_tx_amount"]))

        credit_cats = profile["credit_categories"]
        for _ in range(n_txs):
            hour     = random.randint(h_start, h_end - 1)
            ts       = date.replace(hour=hour, minute=random.randint(0, 59),
                                    second=random.randint(0, 59))
            cat      = random.choice(credit_cats)
            amount   = abs(random.gauss(profile["avg_tx_amount"],
                                        profile["avg_tx_amount"] * 0.5))
            amount   = max(10, round(amount, 2))
            tags     = ["sale"]
            if is_peak:
                tags.append("peak_day")
            txs.append(self._credit(ts, cat, amount, tags=tags))

        return txs

    # ------------------------------------------------------------------
    # Daily variable expenses
    # ------------------------------------------------------------------

    def _daily_expenses(self, date: datetime) -> List[Transaction]:
        txs: List[Transaction] = []
        debit_cats = self.profile["debit_categories"]
        # 1-4 variable expenses per day (excluding fixed costs)
        variable_cats = [c for c in debit_cats
                         if c not in ("rent", "salaries", "insurance", "pos_fees", "subscriptions")]
        n = random.randint(1, 4)
        for _ in range(n):
            cat    = random.choice(variable_cats)
            hour   = random.randint(8, 18)
            ts     = date.replace(hour=hour, minute=random.randint(0, 59))
            amount = abs(random.gauss(800, 600))
            amount = max(50, round(amount, 2))
            tags   = ["expense"]

            # Mark inventory orders so we can simulate idle inventory
            if cat in ("inventory_purchase", "raw_materials"):
                order_id = self._make_id()
                tags.append("inventory_order")
                tx = self._debit(ts, cat, amount, tags=tags,
                                 desc=f"Stock order #{order_id[:8]}")
                # Register as pending order (may or may not resolve)
                self._pending_orders.append({
                    "tx_id"   : tx.id,
                    "amount"  : amount,
                    "date"    : date,
                    "resolved": False,
                })
                txs.append(tx)
            else:
                txs.append(self._debit(ts, cat, amount, tags=tags))

        return txs

    # ------------------------------------------------------------------
    # Anomaly injection
    # ------------------------------------------------------------------

    def _inject_anomalies(self, date: datetime, existing_txs: List[Transaction]) -> List[Transaction]:
        extra: List[Transaction] = []

        if random.random() < self.anomaly_rate:
            # Statistical outlier: very large expense
            cat    = random.choice(self.profile["debit_categories"])
            amount = abs(random.gauss(50_000, 20_000))
            ts     = date.replace(hour=random.randint(0, 23),
                                  minute=random.randint(0, 59))
            tx     = self._debit(ts, cat, amount,
                                 tags=["anomaly", "large_expense"],
                                 desc=f"[ANOMALY] Large {cat} payment")
            extra.append(tx)

        if random.random() < self.anomaly_rate * 0.5 and existing_txs:
            # Duplicate payment: clone a random existing tx
            src = random.choice(existing_txs)
            if src.type == TransactionType.DEBIT:
                ts = src.timestamp + timedelta(minutes=random.randint(5, 180))
                tx = self._debit(ts, src.category, src.amount,
                                 tags=["anomaly", "duplicate"],
                                 desc=f"[DUPLICATE] {src.description}")
                extra.append(tx)

        if random.random() < self.anomaly_rate * 0.3:
            # Unusual timing: transaction at 2–4 AM
            cat    = random.choice(self.profile["debit_categories"])
            amount = abs(random.gauss(5_000, 2_000))
            ts     = date.replace(hour=random.randint(1, 4),
                                  minute=random.randint(0, 59))
            tx     = self._debit(ts, cat, amount,
                                 tags=["anomaly", "unusual_timing"],
                                 desc=f"[ODD-HOURS] {cat.replace('_',' ').title()}")
            extra.append(tx)

        return extra

    # ------------------------------------------------------------------
    # Hidden cost injection (small recurring charges)
    # ------------------------------------------------------------------

    def _inject_hidden_costs(self, date: datetime) -> List[Transaction]:
        if random.random() > self.hidden_cost_rate:
            return []
        hidden_charges = [
            ("Dropbox storage upgrade", 299),
            ("LinkedIn Premium", 2_499),
            ("Canva Pro", 499),
            ("Grammarly Business", 999),
            ("ZoomInfo", 4_999),
            ("SMS gateway monthly", 199),
            ("Domain renewal auto", 799),
        ]
        name, amount = random.choice(hidden_charges)
        ts = date.replace(hour=random.randint(0, 5), minute=random.randint(0, 59))
        return [self._debit(ts, "subscriptions", amount,
                            tags=["hidden_cost", "subscription"],
                            desc=f"{name} (auto-charge)")]

    # ------------------------------------------------------------------
    # Idle inventory resolution
    # ------------------------------------------------------------------

    def _resolve_pending_orders(self, current_date: datetime) -> None:
        """Mark old unresolved orders as idle inventory (tag update not needed—
        they already have 'inventory_order' tag; detection is done in pipeline)."""
        for order in self._pending_orders:
            if not order["resolved"]:
                age = (current_date - order["date"]).days
                if age <= 7 and random.random() < 0.7:
                    order["resolved"] = True   # inventory used quickly — good
                elif age > 14:
                    # Stays unresolved = idle inventory anomaly detected later
                    pass

    # ------------------------------------------------------------------
    # Main generation
    # ------------------------------------------------------------------

    def generate_batch(self, n_days: int = 180) -> List[Transaction]:
        """Generate `n_days` of transaction history in batch mode."""
        all_txs: List[Transaction] = []
        current   = self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date  = current + timedelta(days=n_days)

        seen_months: set = set()

        while current <= end_date:
            month_key = (current.year, current.month)
            day_txs: List[Transaction] = []

            # Monthly fixed costs on first encounter of each month
            if month_key not in seen_months:
                seen_months.add(month_key)
                day_txs.extend(self._monthly_fixed(current.year, current.month))

            # Daily revenue & expenses
            day_txs.extend(self._daily_revenue(current))
            day_txs.extend(self._daily_expenses(current))
            day_txs.extend(self._inject_anomalies(current, day_txs))
            day_txs.extend(self._inject_hidden_costs(current))

            self._resolve_pending_orders(current)

            # Sort by timestamp
            day_txs.sort(key=lambda t: t.timestamp)
            all_txs.extend(day_txs)
            current += timedelta(days=1)

        return all_txs

    def save_batch(self, txs: List[Transaction]) -> None:
        """Save a list of transactions to DB and Redis."""
        conn = sqlite3.connect(self.db_path)
        for tx in txs:
            conn.execute("""
                INSERT OR IGNORE INTO transactions
                (id, timestamp, amount, type, category, description, account_balance, business_type, tags)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                tx.id, tx.timestamp.isoformat(), tx.amount, tx.type.value,
                tx.category, tx.description, tx.account_balance,
                tx.business_type.value, ",".join(tx.tags)
            ))
            if self._redis_ok and self.redis:
                try:
                    self.redis.xadd(self.STREAM_KEY, tx.to_redis_dict(), maxlen=5000)
                except Exception:
                    pass
        conn.commit()
        conn.close()
        print(f"[✓] Saved {len(txs)} transactions to {self.db_path}")

    def save_csv(self, txs: List[Transaction], csv_path: str) -> None:
        """Export transactions to a CSV file representing the company's digital ledger."""
        import csv
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "timestamp", "amount", "type", "category",
                "description", "account_balance", "business_type", "tags"
            ])
            for tx in txs:
                writer.writerow([
                    tx.id,
                    tx.timestamp.isoformat(),
                    tx.amount,
                    tx.type.value if hasattr(tx.type, "value") else str(tx.type),
                    tx.category,
                    tx.description,
                    tx.account_balance,
                    tx.business_type.value if hasattr(tx.business_type, "value") else str(tx.business_type),
                    ",".join(tx.tags) if isinstance(tx.tags, list) else str(tx.tags)
                ])
        print(f"[✓] Exported {len(txs)} transactions to CSV ledger: {csv_path}")

    def run_live(self, interval_seconds: float = 2.0) -> None:
        """Stream a new transaction every `interval_seconds` to Redis + DB."""
        print(f"[LIVE] Streaming transactions every {interval_seconds}s  (Ctrl-C to stop)")
        while True:
            now       = datetime.utcnow()
            day_txs   = self._daily_revenue(now) + self._daily_expenses(now)
            if not day_txs:
                time.sleep(interval_seconds)
                continue
            tx = random.choice(day_txs)
            tx = tx.model_copy(update={"timestamp": now})
            self._insert_db(tx)
            self._publish_redis(tx)
            print(f"  → {tx.id}  {tx.type.value:6}  ₹{tx.amount:>10,.2f}  {tx.category}")
            time.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FinVisor 2.0 Transaction Simulator")
    p.add_argument("--mode",     choices=["batch", "live"], default="batch")
    p.add_argument("--count",    type=int,   default=None,
                   help="Number of days to generate in batch mode (default 180)")
    p.add_argument("--business", choices=["retailer", "restaurant", "service_provider"],
                   default=os.getenv("BUSINESS_TYPE", "retailer"))
    p.add_argument("--db",       default="finvisor.db")
    p.add_argument("--redis",    default=os.getenv("REDIS_URL", "redis://localhost:6379"))
    p.add_argument("--interval", type=float, default=2.0,
                   help="Seconds between live transactions")
    p.add_argument("--csv",      default=None,
                   help="Optional CSV file path to export the digital ledger")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    sim = SMESimulator(
        business_type = args.business,
        db_path       = args.db,
        redis_url     = args.redis,
    )

    if args.mode == "batch":
        n_days = args.count or 180
        print(f"[BATCH] Generating ~{n_days} days of {args.business} transactions …")
        txs = sim.generate_batch(n_days=n_days)
        print(f"[BATCH] Generated {len(txs)} transactions. Saving …")
        sim.save_batch(txs)
        if args.csv:
            sim.save_csv(txs, args.csv)
        print("[BATCH] Done.")
    else:
        sim.run_live(interval_seconds=args.interval)


if __name__ == "__main__":
    main()
