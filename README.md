# DataGuard — Risk-Aware Autonomous Data Quality Operations

> **Thesis:** "Uncertainty is not something the AI should hide. It is a routing signal."

## What is DataGuard?

DataGuard is an AI-powered data quality platform that knows:
- **When it CAN act** (AUTO) — deterministic, reversible, low-impact repairs
- **When it MUST ask** (ESCALATE) — factual uncertainty, missing policy, insufficient authority
- **When it MUST refuse** (BLOCK) — unsupported inputs, security violations

Unlike traditional data cleaning tools that silently "fix" everything, DataGuard uses **Dempster-Shafer evidential reasoning** to quantify uncertainty and make transparent decisions.

## Quick Start

```bash
# 1. Clone and setup
cd dataguard
cp .env.example .env
# Edit .env with your OpenAI API key

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Start backend
make api

# 4. Start frontend (in another terminal)
cd apps/web && npm install && npm run dev

# 5. Open browser
open http://localhost:3000
```

## Architecture

```
Upload → Ingestion → Profiling → Detection → Evidence → D-S Fusion → Autonomy Gate → Action
                                                                          │
                                                                    ┌─────┴─────┐
                                                                    │           │
                                                                 AUTO      ESCALATE/BLOCK
                                                                    │           │
                                                               Auto-fix    Human Review
                                                                    │           │
                                                                    └─────┬─────┘
                                                                          │
                                                                    Audit Ledger
```

## Key Components

| Module | Purpose |
|--------|---------|
| `core/ingestion/` | CSV/XLSX/Parquet parser with encoding detection |
| `core/profiling/` | Column-level statistics, semantic type inference |
| `core/detectors/` | 9 deterministic detectors (pattern, null, outlier, FD, etc.) |
| `core/fusion/` | Dempster-Shafer evidential fusion |
| `core/decisions/` | Autonomy Gate — deterministic decision code |
| `core/audit/` | Immutable audit ledger |
| `apps/api/` | FastAPI REST API |
| `apps/web/` | Next.js dashboard |

## Verify Harness

```bash
# Run all 5 competition verify cases
curl -s -X POST http://localhost:8000/api/verify | python -m json.tool
```

| Case | Description | Expected |
|------|-------------|----------|
| V1 | Whitespace normalization | AUTO |
| V2 | Date format normalization | AUTO |
| V3 | Duplicate key detection | AUTO/ESCALATE |
| V4 | Factual uncertainty (outlier) | ESCALATE |
| V5 | Authority escalation (financial) | ESCALATE |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/datasets` | Upload and analyze dataset |
| GET | `/api/datasets` | List all datasets |
| GET | `/api/datasets/{id}` | Get dataset details + decisions |
| GET | `/api/reviews` | List review queue |
| POST | `/api/reviews/{id}/approve` | Approve escalated decision |
| POST | `/api/reviews/{id}/edit` | Edit and approve |
| POST | `/api/reviews/{id}/reject` | Reject decision |
| GET | `/api/audit` | Query audit trail |
| POST | `/api/verify` | Run verify harness |

## Competition

- **Track:** MLAI Hackathon 2026, Board A: The Escalation Referee
- **Team:** DataGuard
