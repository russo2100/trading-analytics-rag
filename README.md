# 🚀 Trading Analytics RAG System

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Phase%201%20Complete-success.svg)]()

Production-grade **RAG (Retrieval-Augmented Generation)** system for natural gas trading analytics. Portfolio project demonstrating LLMOps best practices: multi-source data ingestion, hybrid retrieval, evaluation-driven development, and agentic workflows.

---

## 🎯 Project Goals

| Goal | Description |
|------|-------------|
| **Multi-source KB** | Ingest trading bot logs (JSONL), market reports (PDF), news articles (TXT/MD) |
| **Hybrid Retrieval** | BM25 + dense embeddings + reranking for high precision/recall |
| **Production-ready** | FastAPI service, Docker Compose, monitoring, security (anti-injection) |
| **Measurable Quality** | Gold Q/A dataset, automated evaluation (Ragas-like metrics) |
| **Portfolio Value** | Clean code, reproducible setup, documented design decisions |

---

## 📊 Current Status

### Phase 1: Foundation ✅

| Component | Status | Details |
|-----------|:------:|---------|
| **Data Schema** | ✅ | SQLite: `trading_events`, `sessions`, `trades`, `broker_trades` |
| **Ingestion Pipeline** | ✅ | Multi-format support (JSONL v1/v2, PDF, TXT) |
| **Data Quality** | ✅ | 1,041 events, 26 trades, 0 NULL/duplicates |
| **Deduplication** | ✅ | Deterministic event IDs, integrity checks |

### Phase 2: Retrieval 🚧

| Component | Status | Details |
|-----------|:------:|---------|
| **Vector Store** | 🚧 | Weaviate/FAISS integration |
| **Hybrid Search** | ⏳ | BM25 + dense retrieval |
| **Reranking** | ⏳ | Cross-encoder for top-K refinement |
| **Evaluation** | ⏳ | Gold Q/A dataset + metrics |

### Phases 3-5: Planned

- **Phase 3**: Generation (LLM integration, prompt engineering, citation tracking)
- **Phase 4**: Agents (task planning, multi-step reasoning, tool calling)
- **Phase 5**: Production (FastAPI, Docker, monitoring, CI/CD)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER QUERY                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: AGENTS                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  • Task Decomposition  • Multi-step Reasoning            │   │
│  │  • Tool Calling (SQL, calculations, external APIs)       │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: GENERATION                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  • LLM Integration (OpenRouter, local models)            │   │
│  │  • Prompt Engineering  • Citation Tracking               │   │
│  │  • Anti-injection Guards  • Context Compression          │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: RETRIEVAL                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Hybrid Search                                           │   │
│  │  ├─ BM25 (keyword)      ┐                                │   │
│  │  ├─ Dense (embeddings)  ├─ Reranking ─> Top-K Results   │   │
│  │  └─ Query Expansion     ┘                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: STORAGE                                               │
│  ┌────────────────────┐      ┌─────────────────────────────┐   │
│  │  SQLite (FTS5)     │      │  Vector DB (Weaviate/FAISS) │   │
│  │  • Metadata        │      │  • Embeddings               │   │
│  │  • Full-text index │      │  • Dense retrieval          │   │
│  └────────────────────┘      └─────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: INGESTION                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Multi-format Loaders                                    │   │
│  │  ├─ JSONL (bot logs v1/v2)                               │   │
│  │  ├─ PDF (broker reports, EIA docs)                       │   │
│  │  ├─ TXT/MD (news articles)                               │   │
│  │  └─ CSV (trade history)                                  │   │
│  │                                                           │   │
│  │  Normalization → Deduplication → Validation              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             ▲
                             │
                    ┌────────┴────────┐
                    │  DATA SOURCES   │
                    └─────────────────┘
```

---

## 📁 Project Structure

```
trading-analytics-rag/
│
├── 📂 src/                           # Source code (layered architecture)
│   ├── layer1_ingestion/            # Data loaders, normalizers, validators
│   │   ├── loaders.py              # JSONL, PDF, TXT parsers
│   │   ├── normalizers.py          # v1/v2 format normalization
│   │   ├── deduplication.py        # Event deduplication logic
│   │   └── models.py               # Pydantic data models
│   │
│   ├── layer2_storage/              # Database clients
│   │   ├── metadata_store.py       # SQLite client (FTS5)
│   │   ├── vector_store.py         # Weaviate/FAISS wrapper
│   │   └── schema.sql              # Database schema (trading + RAG tables)
│   │
│   ├── layer3_retrieval/            # Search & ranking
│   │   ├── query_router.py         # Route queries to appropriate index
│   │   ├── hybrid_search.py        # BM25 + dense fusion
│   │   └── reranker.py             # Cross-encoder reranking
│   │
│   ├── layer4_generation/           # LLM integration
│   │   ├── answer_generator.py     # LLM wrapper (OpenRouter, local)
│   │   ├── prompt_templates.py     # Prompt engineering
│   │   └── citation_tracker.py     # Source attribution
│   │
│   ├── layer5_agents/               # Agentic workflows
│   │   ├── task_planner.py         # Multi-step reasoning
│   │   └── tools.py                # SQL executor, calculators
│   │
│   └── config.py                    # Global configuration
│
├── 📂 scripts/                       # CLI tools
│   ├── init_database.py            # Initialize DB schema
│   ├── ingest_trading_logs.py      # Import trading bot logs
│   ├── check_database.py           # Data quality checks
│   └── run_eval.py                 # Evaluation pipeline
│
├── 📂 data/                          # Data files (gitignored)
│   ├── raw/                        # Source files (JSONL, PDF, TXT)
│   ├── eval/                       # Gold Q/A dataset
│   ├── vector_index/               # Vector DB index
│   └── metadata.db                 # SQLite database
│
├── 📂 docs/                          # Documentation
│   ├── architecture.md             # Design decisions
│   ├── eval_baseline.md            # Baseline metrics
│   └── roadmap.md                  # Development roadmap
│
├── 📂 tests/                         # Tests
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── fixtures/                   # Test data
│
├── .env.example                     # Environment template
├── .gitignore                       # Git ignore rules
├── requirements.txt                 # Python dependencies
├── docker-compose.yml               # Local dev stack
├── LICENSE                          # MIT License
└── README.md                        # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11 or higher
- **SQLite**: 3.35+ (for FTS5 support)
- **Docker** (optional): For Weaviate vector database

### Installation

```bash
# 1. Clone repository
git clone https://github.com/russo2100/trading-analytics-rag.git
cd trading-analytics-rag

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env: add API keys (OpenRouter, etc.)
```

### Initialize Database

```bash
# Create tables from schema.sql
python scripts/init_database.py

# Import sample trading logs (if available)
python scripts/ingest_trading_logs.py --source data/raw/logs.jsonl

# Verify data quality
python scripts/check_database.py
```

**Expected output:**
```
📊 Database: data/metadata.db
📋 Tables (12):
   • trading_events: 1,041 rows
   • sessions: 2 rows
   • trades: 26 rows
   
⚠️  Data quality checks:
   • NULL actions: 0
   • Duplicate event_ids: 0
   • Orphaned trades: 0
```

---

## 📈 Data Schema

### Core Tables

#### `trading_events` — Bot decision log
| Field | Type | Description |
|-------|------|-------------|
| `event_id` | TEXT PK | Deterministic ID (YYYYMMDD_cycle_unix) |
| `session_id` | TEXT | Daily session (YYYYMMDD) |
| `timestamp` | TEXT | ISO 8601 timestamp |
| `cycle` | INTEGER | Iteration number within session |
| `price` | REAL | Market price (USD) |
| `rsi` | REAL | RSI indicator |
| `lots` | INTEGER | Position size |
| `pnl_pct` | REAL | Current P&L (%) |
| `action` | TEXT | Decision (BUY/SELL/NOOP) |
| `reason` | TEXT | Decision rationale |
| `ai_signal` | TEXT | AI recommendation |
| `ai_confidence` | INTEGER | Confidence score (0-100) |

#### `sessions` — Daily aggregates
| Field | Type | Description |
|-------|------|-------------|
| `session_id` | TEXT PK | Date (YYYYMMDD) |
| `date` | TEXT | ISO date |
| `total_cycles` | INTEGER | Total iterations |
| `total_trades` | INTEGER | Count of non-NOOP actions |
| `final_lots` | INTEGER | End-of-day position |
| `final_pnl_pct` | REAL | Final P&L (%) |

#### `trades` — Executed actions only
| Field | Type | Description |
|-------|------|-------------|
| `trade_id` | TEXT PK | Same as event_id |
| `event_id` | TEXT FK | Link to trading_events |
| `action` | TEXT | BUY/SELL |
| `lots_changed` | INTEGER | Net change (+/-) |
| `price_usd` | REAL | Execution price |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html tests/

# Run specific test suite
pytest tests/unit/test_normalizers.py -v

# Run integration tests only
pytest tests/integration/ -v
```

---

## 🛡️ Security & Best Practices

### Implemented

✅ **Prompt injection protection**: All retrieved context treated as untrusted data  
✅ **Secrets management**: `.env` file (gitignored), no hardcoded API keys  
✅ **Input validation**: Pydantic models for all external inputs  
✅ **Deterministic IDs**: Event IDs prevent duplicates and enable idempotent ingestion  

### Planned

⏳ **Rate limiting**: API request throttling  
⏳ **PII detection**: Automatic redaction of sensitive data  
⏳ **Audit logging**: All queries and retrieval results logged  

---

## 📚 Documentation

- **[Architecture & Design Decisions](docs/architecture.md)** — System design rationale
- **[RAG/KAG Roadmap](docs/roadmap.md)** — 12-month development plan
- **[Evaluation Methodology](docs/eval_baseline.md)** — Metrics and baselines

---

## 📝 License

MIT License — see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Руслан Латыпов**  
AI/ML Engineer | RAG/KAG Systems | LangChain/LlamaIndex  

[![GitHub](https://img.shields.io/badge/GitHub-russo2100-181717?logo=github)](https://github.com/russo2100)
[![Portfolio](https://img.shields.io/badge/Portfolio-View-blue)](https://github.com/russo2100/trading-analytics-rag)

---

## 📌 Project Status

**Phase 1 (Foundation)**: ✅ Complete  
**Phase 2 (Retrieval)**: 🚧 In Progress  
**Last Updated**: February 1, 2026

---

<div align="center">
  <sub>Built with ❤️ for production AI systems</sub>
</div>
