# DAG System для NG Фьючерсов (EventHorizon Trading AI)

**Decision-Augmented Generation (DAG) система** для генерации торговых сигналов по фьючерсам Natural Gas (NG), торгуемым через Т-Инвестиции.

---

## 🎯 Цель проекта

Производственная RAG/DAG система, которая:
- Анализирует фундаментальные данные (EIA storage, погода, новости)
- Генерирует торговые сигналы (BUY/SELL/HOLD + лоты + confidence + reasoning)
- Работает как portfolio-проект уровня Middle+ ML Engineer

**Ключевое отличие от generic RAG:**
- Не просто поиск по документам, а **принятие торговых решений**
- Детерминированные правила (Stage 1) + LLM explanation (Stage 2)
- Confidence score — агрегация доказательств, НЕ угадывание LLM

---

## 🏗️ Архитектура (7-слойная DAG)

Layer 1: Ingestion & Normalization
Layer 2: Storage & Indexing (FAISS + SQLite)
Layer 3: Hybrid Retrieval (Vector + Keyword + RRF)
Layer 4: Context Scoring (Relevance + Freshness + Authority)
Layer 5: Decision Logic (Deterministic Rules + LLM Reasoning)
Layer 6: Confidence Scoring (Evidence Aggregation)
Layer 7: Output & Governance (Validation + Audit)

text

См. полную схему в `docs/architecture.md`

---

## 🚀 Quickstart

### 1. Установка

```bash
# Клонировать (или скопировать папку)
cd lesson_3

# Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Установить зависимости
pip install -r requirements.txt
2. Настройка
bash
# Скопировать шаблон .env
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Отредактировать .env (добавить API ключи)
notepad .env  # Windows
# nano .env  # Linux/Mac
Обязательные ключи:

OPENROUTER_API_KEY — для LLM (Claude 3.5 Sonnet)

EIA_API_KEY — для данных по storage/production

3. Запуск (Week 1 — Ingestion)
bash
# Загрузить данные из логов бота
python scripts/ingest_logs.py --source data/raw/logs.jsonl

# Построить векторный индекс
python scripts/build_index.py
📁 Структура проекта
text
lesson_3/
├── src/
│   ├── layer1_ingestion/   # JSONL, EIA API, нормализация
│   ├── layer2_storage/     # FAISS + SQLite
│   ├── layer3_retrieval/   # Hybrid search (Week 2)
│   ├── layer4_scoring/     # Context scoring (Week 2)
│   ├── layer5_decision/    # Rules + LLM (Week 3)
│   ├── layer6_confidence/  # Evidence aggregation (Week 3)
│   └── layer7_validation/  # Governance (Week 4)
├── tests/                  # Unit + Integration тесты
├── data/
│   ├── raw/                # JSONL логи от бота
│   ├── processed/          # Ingested events
│   └── vector_index/       # FAISS индекс
├── scripts/                # CLI утилиты
└── docs/                   # Документация

🧪 Тестирование
bash
# Запустить все тесты
pytest tests/

# Только unit-тесты ingestion
pytest tests/test_ingestion.py -v

# С покрытием
pytest --cov=src tests/
📊 Roadmap
 Week 0: Методологический анализ (TRD → DAG architecture)

 Week 1: Layer 1 (Ingestion) + Layer 2 (Storage)

 Week 2: Layer 3 (Retrieval) + Layer 4 (Scoring)

 Week 3: Layer 5 (Decision) + Layer 6 (Confidence)

 Week 4: Layer 7 (Validation) + Integration с ботом

📖 Документация
Архитектура — полная диаграмма 7 слоёв

Торговые правила — детерминированные правила (твоя зона)

Evaluation plan — synthetic scenarios + baseline

🛡️ Security
⚠️ НИКОГДА не коммитьте .env файл!

Все API ключи должны быть в .env (ignored by git). Используй .env.example как шаблон.

📝 License
Proprietary (Portfolio project)

👤 Author
Руслан (russo2100) — ML/AI Engineer, EventHorizon Trading AI

text

***

## **Файл 3: `requirements.txt`**

```txt
# Core
pydantic==2.9.2
pydantic-settings==2.6.1
python-dotenv==1.0.1

# Data processing
pandas==2.2.3
numpy==1.26.4

# Vector store
faiss-cpu==1.9.0
sentence-transformers==3.3.1

# Metadata store
sqlalchemy==2.0.36

# API clients
httpx==0.28.1
feedparser==6.0.11  # для EIA RSS

# LLM (через OpenRouter)
openai==1.58.1  # OpenRouter совместим с OpenAI SDK

# Testing
pytest==8.3.4
pytest-asyncio==0.25.2
pytest-cov==6.0.0

# Utilities
pytz==2024.2