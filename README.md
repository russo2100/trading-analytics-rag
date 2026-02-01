# EventHorizon RAG/KAG System

Production-grade RAG (Retrieval-Augmented Generation) system for natural gas trading analytics. Built as a portfolio project demonstrating best practices for LLMOps: multi-source ingestion, hybrid retrieval, evaluation-driven development, agentic workflows.

## 🎯 Project Goals

1. **Multi-source knowledge base**: Ingest trading bot logs (JSONL), market reports (PDF), news (TXT/MD)
2. **Hybrid retrieval**: BM25 + dense embeddings + reranking for high precision/recall
3. **Production-ready**: FastAPI service, Docker compose, monitoring, security (anti-injection)
4. **Measurable quality**: Gold Q/A dataset, automated evaluation (Ragas-like metrics)
5. **Portfolio value**: Clean code, reproducible, documented design decisions

## 📊 Current Status (Phase 1: Foundation)

| Component | Status | Details |
|-----------|--------|---------|
| Data Schema | ✅ Done | SQLite: `trading_events`, `sessions`, `trades` |
| Ingestion | ✅ Done | `ingest_trading_logs.py` (v1/v2 support) |
| Data Quality | ✅ Done | 1041 events, 26 trades, 0 NULL/duplicates |
| Vector Store | 🚧 In Progress | Weaviate/FAISS integration |
| Retrieval | ⏳ Planned | Hybrid BM25 + dense |
| Generation | ⏳ Planned | LangChain + OpenRouter |
| Evaluation | ⏳ Planned | Gold Q/A + metrics |

## 🏗️ Architecture

┌─────────────────┐
│ Layer 1: Data │ Multi-format loaders (JSONL, PDF, TXT)
│ Ingestion │ Normalization, deduplication, validation
└────────┬────────┘
│
┌────────▼────────┐
│ Layer 2: │ SQLite (metadata + FTS5)
│ Storage │ Vector DB (embeddings)
└────────┬────────┘
│
┌────────▼────────┐
│ Layer 3: │ Hybrid search (BM25 + dense)
│ Retrieval │ Query routing, reranking
└────────┬────────┘
│
┌────────▼────────┐
│ Layer 4: │ LLM integration (OpenRouter/local)
│ Generation │ Prompt engineering, citation tracking
└────────┬────────┘
│
┌────────▼────────┐
│ Layer 5: │ Task planning, multi-step reasoning
│ Agents │ Tool calling (SQL, calculations)
└─────────────────┘

text

## 📁 Project Structure

eventhorizon-rag/
├── src/
│ ├── layer1_ingestion/ # Data loaders, normalizers
│ ├── layer2_storage/ # DB clients (SQLite, Weaviate)
│ ├── layer3_retrieval/ # Search, reranking
│ ├── layer4_generation/ # LLM wrappers
│ └── layer5_agents/ # Agentic workflows
├── scripts/
│ ├── ingest_trading_logs.py # Trading logs → SQLite
│ ├── init_database.py # Schema initialization
│ ├── check_database.py # Data quality checks
│ └── run_eval.py # Evaluation pipeline
├── data/
│ ├── raw/ # Source files (gitignored)
│ ├── eval/ # Gold Q/A dataset
│ └── vector_index/ # Vector DB index
├── docs/
│ ├── architecture.md # Design decisions
│ ├── eval_baseline.md # Baseline metrics
│ └── roadmap.md # Development plan
├── tests/
│ ├── unit/ # Unit tests
│ └── integration/ # Integration tests
├── .env.example # Environment template
├── requirements.txt # Python dependencies
├── docker-compose.yml # Local dev stack
└── README.md # This file

text

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- SQLite 3.35+ (for FTS5)
- (Optional) Docker for Weaviate

### Installation

```bash
# Clone repo
git clone https://github.com/russo2100/eventhorizon-rag.git
cd eventhorizon-rag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env: add API keys (OpenRouter, etc.)
Initialize Database
bash
# Create tables
python scripts/init_database.py

# Import sample data (if you have trading logs)
python scripts/ingest_trading_logs.py --source data/raw/logs.jsonl

# Verify
python scripts/check_database.py
📈 Data Schema
trading_events (bot decisions)
event_id (PK): Deterministic (YYYYMMDD_cycle_unix)

session_id: Daily session (YYYYMMDD)

timestamp, cycle, price, rsi, lots, pnl_pct

action (BUY/SELL/NOOP), reason, ai_signal, ai_confidence

sessions (daily aggregates)
session_id (PK)

total_cycles, total_trades, final_lots, final_pnl_pct

trades (non-NOOP actions)
trade_id, event_id (FK), action, lots_changed, price_usd

🧪 Testing
bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific suite
pytest tests/unit/test_normalizers.py
📚 Documentation
Architecture & Design

RAG/KAG Roadmap

Evaluation Methodology

🛡️ Security
Prompt injection protection: Retrieved context treated as untrusted data

Secrets management: .env file (gitignored), no hardcoded keys

Input validation: Pydantic models for all external data

📝 License
MIT License - see LICENSE file

👤 Author
Руслан Латыпов (@russo2100)
AI/ML Engineer | RAG/KAG Systems | LangChain/LlamaIndex

Status: Active development (Phase 1: Foundation ✅ | Phase 2: Retrieval 🚧)

Last updated: 2026-02-01

