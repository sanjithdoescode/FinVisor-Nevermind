# FinVisor 2.0 — AI-Powered Financial Advisor for SMEs

## Architecture

```
FinVisor_2.0/
├── simulator/
│   ├── __init__.py
│   ├── schemas.py          # Pydantic data models (shared)
│   └── simulator.py        # Transaction generator (batch + live)
├── backend/
│   ├── __init__.py
│   ├── main.py             # FastAPI app & routes
│   ├── db.py               # SQLite (aiosqlite) layer
│   ├── redis_client.py     # Redis stream utilities
│   ├── pipeline.py         # Analysis orchestrator
│   ├── anomaly.py          # Anomaly detection engine
│   ├── recurring.py        # Recurring cost detector
│   ├── advisor.py          # Mistral AI advisor
│   └── whatif.py           # What-if scenario simulator
├── .env                    # Local environment variables
├── .env.example            # Template
├── docker-compose.yml      # Redis service
└── requirements.txt
```

## Quick Start

### 1. Start Redis
```bash
docker-compose up -d
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env and set your MISTRAL_API_KEY
```

### 4. Generate transaction data
```bash
# Generate 180 days of retailer data (batch mode)
python simulator/simulator.py --mode batch --business retailer

# OR stream live transactions every 2 seconds
python simulator/simulator.py --mode live --interval 2
```

### 5. Start the API server
```bash
uvicorn backend.main:app --reload --port 8000
```

### 6. Start the React Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
# Dashboard opens at http://localhost:5173
```

### 7. Trigger analysis
```bash
curl -X POST http://localhost:8000/analyze
```

---

## API Endpoints

| Method | Endpoint             | Description                              |
|--------|----------------------|------------------------------------------|
| GET    | `/health`            | System health check                      |
| GET    | `/transactions`      | Paginated transaction list               |
| GET    | `/transactions/live` | SSE live transaction stream              |
| POST   | `/analyze`           | Run full AI analysis pipeline            |
| GET    | `/report`            | Latest financial health report           |
| GET    | `/anomalies`         | Detected anomalies with evidence         |
| GET    | `/recurring`         | Recurring & hidden costs                 |
| POST   | `/whatif`            | What-if scenario simulation              |
| GET    | `/whatif/history`    | Previous what-if scenarios               |
| WS     | `/ws/live`           | WebSocket live transaction feed          |

### Swagger UI
```
http://localhost:8000/docs
```

---

## What-If Scenario Examples

```bash
# Reduce marketing spending by 20%
curl -X POST http://localhost:8000/whatif \
  -H "Content-Type: application/json" \
  -d '{"scenario_type":"reduce_category","parameters":{"category":"marketing","reduction_pct":20},"description":"Cut marketing by 20%"}'

# Increase sales by 15%
curl -X POST http://localhost:8000/whatif \
  -H "Content-Type: application/json" \
  -d '{"scenario_type":"increase_sales","parameters":{"increase_pct":15}}'

# Eliminate Salesforce subscription
curl -X POST http://localhost:8000/whatif \
  -H "Content-Type: application/json" \
  -d '{"scenario_type":"eliminate_subscription","parameters":{"keyword":"salesforce"}}'
```

---

## Anomaly Detection

The engine detects:
- **Statistical outliers** — Z-score > 2.5 on amount within category  
- **Duplicate payments** — Same amount + category within 24 hours  
- **Unusual timing** — Transactions at 01:00–04:00  
- **Budget violations** — Category spending > configured threshold  
- **Idle inventory** — Orders with no matching sales for 14+ days  
- **Irregular income** — Feast/famine revenue patterns (high CV)  

---

## Recurring Cost Detection

Identifies:
- **Subscriptions** — Fixed monthly SaaS charges
- **Recurring costs** — Regular vendor/category payments
- **Hidden costs** — Small, frequent, often-overlooked charges

---

## Simulator Business Types

| Type               | Avg Daily Revenue | Key Categories                    |
|--------------------|------------------|-----------------------------------|
| `retailer`         | ₹8,500           | product_sales, inventory, rent    |
| `restaurant`       | ₹14,000          | dine_in, raw_materials, delivery  |
| `service_provider` | ₹22,000          | consulting_fee, cloud, salaries   |
