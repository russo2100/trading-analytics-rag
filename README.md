# 🚀 Trading Analytics RAG System

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Production%20Ready-success.svg)]()

Production-grade **RAG (Retrieval-Augmented Generation)** system for natural gas trading analytics. Portfolio project demonstrating LLMOps best practices: multi-source data ingestion, hybrid retrieval, LLM generation, and agentic workflows.

---

## 🎯 Project Goals

| Goal | Description |
|------|-------------|
| **Multi-source KB** | Ingest trading bot logs (JSONL), market reports (PDF), news articles (TXT/MD) |
| **Hybrid Retrieval** | BM25 + dense embeddings + reranking for high precision/recall |
| **LLM Generation** | Context-aware answer generation with citation tracking |
| **Agentic Workflows** | ReAct loop with tools (retrieval, SQL, calculator) |
| **Production-ready** | Tests, docs, monitoring, security (anti-injection) |

---

## 📊 Current Status

### ✅ ALL PHASES COMPLETE

| Phase | Components | Status |
|-------|-----------|:------:|
| **Phase 1: Foundation** | Multi-format ingestion + SQLite/FAISS storage | ✅ 100% |
| **Phase 2: Retrieval** | Hybrid search (BM25 + dense) + reranking | ✅ 100% |
| **Phase 3: Generation** | LLM integration (OpenRouter) + prompts | ✅ 100% |
| **Phase 4: Agents** | ReAct loop + tools (retrieval, SQL) | ✅ 100% |
| **Phase 5: Production** | Tests + docs + utilities | ✅ 100% |

### 📈 Project Metrics

| Metric | Value |
|--------|-------|
| **Lines of Code** | 2,500+ |
| **Test Coverage** | VectorStore: 100% |
| **Scripts** | 16 production utilities |
| **Documentation** | 4 comprehensive guides |
| **Data Quality** | 1,041 events, 0 duplicates |

---

## 🎬 Quick Demo

### Option 1: Interactive Agent

```bash
# Start interactive trading analyst
python scripts/test_agent.py --interactive

> Query: How many trades were executed on January 30?
> Agent: On January 30, 2026, there were 7 trades executed...
```

### Option 2: Python API

```python
from src.layer5_agents import TradingAgent

# Initialize agent
agent = TradingAgent()

# Ask a question
response = agent.query("What was the PnL on Jan 29?")
print(response)

# Output:
# The final P&L for January 29 was +2.3%. 
# Session started at 16:32 and ended at 23:49.
# Total trades: 19 (14 BUY, 5 SELL)
# Source: trading_events table, session 20260129
```

### Option 3: Test Specific Layers

```bash
# Test vector search
python scripts/test_vector_search.py --query "high volatility trades"

# Test LLM generation
python scripts/test_generation.py --question "Explain RSI indicator"

# Test RAG pipeline
python scripts/test_rag_pipeline.py
```

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
│  │  • ReAct Loop (Reason → Act → Observe)                   │   │
│  │  • Tools: Retrieval, SQL Executor, Calculator            │   │
│  │  • Memory: Conversation History                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: GENERATION                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  • LLM: OpenRouter (Claude 3.5 Sonnet, GPT-4)            │   │
│  │  • Prompts: Trading Expert Persona                       │   │
│  │  • Citation Tracking: Source attribution                 │   │
│  │  • Anti-injection Guards: Context sanitization           │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: RETRIEVAL                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Hybrid Search                                           │   │
│  │  ├─ BM25 (keyword)      ┐                                │   │
│  │  ├─ Dense (embeddings)  ├─ Fusion ─> Reranking ─> Top-K │   │
│  │  └─ Query Expansion     ┘                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: STORAGE                                               │
│  ┌────────────────────┐      ┌─────────────────────────────┐   │
│  │  SQLite (FTS5)     │      │  FAISS Vector Store         │   │
│  │  • Metadata        │      │  • sentence-transformers    │   │
│  │  • Full-text index │      │  • Dense retrieval          │   │
│  │  • 1,041 events    │      │  • Semantic search          │   │
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
│   ├── layer1_ingestion/            # Data loaders, normalizers
│   │   ├── loaders.py              # JSONL, PDF, TXT parsers
│   │   └── normalizers.py          # v1/v2 format normalization
│   │
│   ├── layer2_storage/              # Database clients
│   │   ├── metadata_store.py       # SQLite + FTS5
│   │   ├── vector_store.py         # FAISS wrapper (290 LOC)
│   │   └── schema.sql              # DB schema
│   │
│   ├── layer3_retrieval/            # Search & ranking
│   │   ├── hybrid_search.py        # BM25 + dense fusion
│   │   ├── reranker.py             # Cross-encoder
│   │   └── query_router.py         # Smart routing
│   │
│   ├── layer4_generation/           # LLM integration
│   │   ├── answer_generator.py     # OpenRouter client
│   │   ├── prompt_templates.py     # Trading prompts
│   │   └── citation_tracker.py     # Source attribution
│   │
│   ├── layer5_agents/               # Agentic workflows
│   │   ├── react_agent.py          # ReAct loop
│   │   └── tools.py                # Retrieval, SQL, math tools
│   │
│   └── config.py                    # Global configuration
│
├── 📂 scripts/                       # CLI utilities (16 tools)
│   ├── init_database.py            # Initialize DB schema
│   ├── ingest_trading_logs.py      # Import bot logs
│   ├── build_vector_index.py       # Build FAISS index
│   ├── test_vector_search.py       # Interactive search test
│   ├── test_agent.py               # Agent testing
│   ├── test_rag_pipeline.py        # End-to-end test
│   └── check_database.py           # Data quality checks
│
├── 📂 tests/                         # Test suite
│   ├── test_vector_store.py        # VectorStore tests (263 LOC)
│   ├── test_retrieval.py           # Retrieval tests
│   └── fixtures/                   # Test data
│
├── 📂 docs/                          # Documentation
│   ├── QUICK_SUMMARY.md            # Project summary
│   ├── ANALYSIS_REPORT.md          # Technical analysis
│   ├── RECOMMENDATIONS.md          # Best practices
│   └── ARCHITECTURE_VISUAL.txt     # Visual diagrams
│
├── .gitignore                       # Git ignore rules
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project metadata
├── CHANGELOG.md                     # Version history
└── README.md                        # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11 or higher
- **SQLite**: 3.35+ (for FTS5 support)
- **GPU** (optional): For faster embeddings

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
# Edit .env: add OpenRouter API key
```

### Initialize System

```bash
# 1. Create database
python scripts/init_database.py

# 2. Import trading logs (if available)
python scripts/ingest_trading_logs.py --source data/raw/logs.jsonl

# 3. Build vector index
python scripts/build_vector_index.py

# 4. Verify setup
python scripts/check_database.py
```

**Expected output:**
```
📊 Database: data/metadata.db
📋 Tables:
   • trading_events: 1,041 rows
   • sessions: 2 rows
   • trades: 26 rows
   
⚠️  Data quality checks:
   • NULL actions: 0
   • Duplicate event_ids: 0
   • Orphaned trades: 0
   
✅ Vector index: data/vector_index/ (1,041 vectors)
```

### Run Interactive Agent

```bash
python scripts/test_agent.py --interactive
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
| `cycle` | INTEGER | Iteration number |
| `price` | REAL | Market price (USD) |
| `rsi` | REAL | RSI indicator |
| `action` | TEXT | Decision (BUY/SELL/NOOP) |
| `reason` | TEXT | Decision rationale |

#### `sessions` — Daily aggregates
| Field | Type | Description |
|-------|------|-------------|
| `session_id` | TEXT PK | Date (YYYYMMDD) |
| `total_cycles` | INTEGER | Total iterations |
| `total_trades` | INTEGER | Count of non-NOOP actions |
| `final_pnl_pct` | REAL | Final P&L (%) |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Test specific component
pytest tests/test_vector_store.py -v

# Interactive tests
python scripts/test_vector_search.py --interactive
python scripts/test_agent.py --interactive
```

---

## 🛡️ Security & Best Practices

### Implemented

✅ **Prompt injection protection**: Retrieved context sanitized  
✅ **Secrets management**: `.env` file (gitignored)  
✅ **Input validation**: Pydantic models for all inputs  
✅ **Deterministic IDs**: Event IDs prevent duplicates  
✅ **Anti-hallucination**: Citation tracking for all claims  

---

## 📚 Documentation

- **[Quick Summary](QUICK_SUMMARY.md)** — Project overview and status
- **[Analysis Report](ANALYSIS_REPORT.md)** — Technical deep dive
- **[Recommendations](RECOMMENDATIONS.md)** — Best practices
- **[Architecture Visual](ARCHITECTURE_VISUAL.txt)** — Detailed diagrams

---

## 🗓️ Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

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

**Production Ready** | All phases complete | Last Updated: February 13, 2026

---

<div align="center">
  <sub>Built with ❤️ for production AI systems</sub>
</div>
