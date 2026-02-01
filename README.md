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

