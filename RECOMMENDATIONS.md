# 🎯 Рекомендации по продолжению работы

## 📋 Приоритетные задачи

### 🔴 КРИТИЧНО - Сделать сегодня

#### 1. Построить векторный индекс
**Проблема**: Векторный индекс не построен, директория `data/vector_index/` пуста.

**Решение**:
```bash
# Активировать виртуальное окружение
venv\Scripts\activate

# Построить индекс из существующих данных
python scripts/build_vector_index.py

# Ожидаемый результат:
# - Создание FAISS индекса
# - Генерация эмбеддингов для 1,041 событий
# - Сохранение в data/vector_index/
```
e
**Проблема**: Таблица `events` пуста (RAG события не загружены).

**Решение**:
```bash
# Сначала нужно загрузить события из trading_events в events
# Создать скрипт для миграции данных или загрузить новые источники
```

#### 2. Установить недостающие зависимости
**Проблема**: `ModuleNotFoundError: No module named 'faiss'`

**Решение**:
```bash
# Проверить установку зависимостей
pip install -r requirements.txt

# Если проблемы с faiss-cpu, попробовать:
pip install faiss-cpu --no-cache-dir

# Для GPU версии (если есть CUDA):
pip install faiss-gpu
```

---

### 🟡 ВАЖНО - Сделать на этой неделе

#### 3. Загрузить данные из разных источников

**EIA Storage Reports**:
```python
# Создать скрипт для загрузки EIA данных
# scripts/ingest_eia_data.py

# Использовать EIA API:
# https://www.eia.gov/opendata/
```

**Weather Data**:
```python
# Интеграция с weather API
# scripts/ingest_weather_data.py
```

**News Articles**:
```python
# Парсинг новостных источников
# scripts/ingest_news.py
```

#### 4. Протестировать векторный поиск

```bash
# Интерактивное тестирование
python scripts/test_vector_search.py --interactive

# Тестовые запросы:
# - "trading decision buy"
# - "market price RSI indicator"
# - "profit and loss"
# - "AI signal confidence"
```

#### 5. Реализовать Hybrid Search

**Файл**: `src/layer3_retrieval/hybrid_search.py`

```python
class HybridSearch:
    def __init__(self, vector_store, metadata_store):
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        
    def search(self, query, top_k=10):
        # 1. BM25 search (SQLite FTS5)
        bm25_results = self._bm25_search(query, top_k * 2)
        
        # 2. Dense search (FAISS)
        dense_results = self.vector_store.search(query, top_k * 2)
        
        # 3. Reciprocal Rank Fusion
        fused_results = self._rrf_fusion(bm25_results, dense_results)
        
        return fused_results[:top_k]
```

---

### 🟢 ЖЕЛАТЕЛЬНО - Сделать в этом месяце

#### 6. Создать Evaluation Dataset

**Файл**: `data/eval/gold_qa.jsonl`

```json
{"question": "Какое решение принял бот 30 января в 11:18?", "answer": "...", "event_ids": ["..."]}
{"question": "Какой был RSI на момент покупки?", "answer": "...", "event_ids": ["..."]}
{"question": "Сколько сделок было совершено 29 января?", "answer": "19", "event_ids": ["..."]}
```

**Скрипт**: `scripts/run_eval.py`

```python
# Метрики:
# - Precision@K
# - Recall@K
# - MRR (Mean Reciprocal Rank)
# - NDCG (Normalized Discounted Cumulative Gain)
```

#### 7. Интегрировать LLM

**Файл**: `src/layer4_generation/answer_generator.py`

```python
from openai import OpenAI

class AnswerGenerator:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key
        )
    
    def generate(self, query, context):
        prompt = self._build_prompt(query, context)
        response = self.client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
```

#### 8. Добавить Reranking

**Файл**: `src/layer3_retrieval/reranker.py`

```python
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self):
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    def rerank(self, query, results, top_k=10):
        # Создать пары (query, document)
        pairs = [(query, r['text']) for r in results]
        
        # Получить scores
        scores = self.model.predict(pairs)
        
        # Отсортировать и вернуть top-K
        reranked = sorted(
            zip(results, scores), 
            key=lambda x: x[1], 
            reverse=True
        )
        return [r for r, s in reranked[:top_k]]
```

---

## 🔧 Технические улучшения

### Оптимизация производительности

#### 1. Использовать IVF индекс для больших данных
```python
# Вместо IndexFlatL2 использовать IndexIVFFlat
# для ускорения поиска на больших датасетах

import faiss

# Обучить quantizer
quantizer = faiss.IndexFlatL2(dimension)
index = faiss.IndexIVFFlat(quantizer, dimension, nlist=100)

# Обучить на данных
index.train(embeddings)
index.add(embeddings)
```

#### 2. Добавить кэширование
```python
# src/layer2_storage/cache.py

from functools import lru_cache
import redis

class QueryCache:
    def __init__(self):
        self.redis_client = redis.Redis() if settings.use_redis else None
    
    @lru_cache(maxsize=1000)
    def get_or_compute(self, query, compute_fn):
        # Проверить кэш
        if self.redis_client:
            cached = self.redis_client.get(query)
            if cached:
                return json.loads(cached)
        
        # Вычислить
        result = compute_fn(query)
        
        # Сохранить в кэш
        if self.redis_client:
            self.redis_client.setex(query, 3600, json.dumps(result))
        
        return result
```

#### 3. Batch processing для эмбеддингов
```python
# Уже реализовано в VectorStore.add_events()
# batch_size=32 для оптимальной производительности
```

---

## 📊 Мониторинг и логирование

### 1. Добавить метрики в query_stats

```python
# При каждом запросе логировать:
# - query_text
# - result_count
# - latency_ms
# - cache_hit

def log_query_stats(query, results, latency, cache_hit):
    cursor.execute("""
        INSERT INTO query_stats 
        (query_text, result_count, latency_ms, cache_hit)
        VALUES (?, ?, ?, ?)
    """, (query, len(results), latency, cache_hit))
```

### 2. Создать dashboard для мониторинга

```python
# scripts/show_stats.py

import sqlite3
import pandas as pd

def show_query_stats():
    conn = sqlite3.connect('data/metadata.db')
    
    # Топ запросов
    df = pd.read_sql("""
        SELECT query_text, COUNT(*) as count, AVG(latency_ms) as avg_latency
        FROM query_stats
        GROUP BY query_text
        ORDER BY count DESC
        LIMIT 10
    """, conn)
    
    print(df)
```

---

## 🧪 Тестирование

### 1. Добавить integration тесты

**Файл**: `tests/integration/test_rag_pipeline.py`

```python
def test_end_to_end_rag():
    # 1. Загрузить данные
    # 2. Построить индекс
    # 3. Выполнить запрос
    # 4. Проверить результаты
    
    query = "Какое решение принял бот?"
    results = rag_pipeline.search(query)
    
    assert len(results) > 0
    assert results[0]['score'] > 0.7
```

### 2. Добавить benchmark тесты

**Файл**: `tests/benchmark/test_performance.py`

```python
import time

def test_search_performance():
    # Измерить время поиска
    start = time.time()
    results = vector_store.search("test query", top_k=100)
    latency = (time.time() - start) * 1000
    
    # Должно быть < 100ms для 1000 векторов
    assert latency < 100
```

---

## 📚 Документация

### 1. Добавить примеры использования

**Файл**: `docs/examples.md`

```markdown
# Примеры использования

## Базовый поиск
```python
from src.layer2_storage.vector_store import VectorStore

vs = VectorStore()
vs.load()

results = vs.search("trading decision", top_k=5)
for r in results:
    print(f"{r['event_id']}: {r['score']:.3f}")
```

## Поиск с фильтрами
```python
results = vs.search(
    "market price",
    top_k=10,
    filter_metadata={'source': 'logs'}
)
```
```

### 2. Создать API документацию

**Файл**: `docs/api.md`

```markdown
# API Reference

## VectorStore

### Methods

#### `add_events(event_ids, texts, metadata)`
Добавить события в векторный индекс.

**Parameters:**
- `event_ids` (List[str]): Список ID событий
- `texts` (List[str]): Тексты для эмбеддинга
- `metadata` (List[Dict]): Метаданные (опционально)

**Returns:** None

**Example:**
```python
vs.add_events(
    ['e1', 'e2'],
    ['text 1', 'text 2'],
    [{'source': 'logs'}, {'source': 'eia'}]
)
```
```

---

## 🚀 Deployment

### 1. Создать FastAPI сервис

**Файл**: `src/api/main.py`

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

@app.post("/search")
async def search(request: SearchRequest):
    results = vector_store.search(request.query, request.top_k)
    return {"results": results}
```

### 2. Добавить Docker

**Файл**: `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Файл**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
```

---

## 📈 Roadmap

### Неделя 1 (текущая)
- [x] Построить векторный индекс
- [x] Протестировать поиск
- [ ] Загрузить EIA данные

### Неделя 2
- [ ] Реализовать hybrid search
- [ ] Добавить reranking
- [ ] Создать eval dataset

### Неделя 3
- [ ] Интегрировать LLM
- [ ] Реализовать RAG pipeline
- [ ] Добавить citation tracking

### Неделя 4
- [ ] Создать FastAPI сервис
- [ ] Добавить Docker
- [ ] Написать документацию

---

## 💡 Советы

### Best Practices

1. **Всегда тестируйте на маленьких данных сначала**
   ```bash
   python scripts/build_vector_index.py --limit 100
   ```

2. **Используйте логирование для отладки**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Сохраняйте промежуточные результаты**
   ```python
   # Сохранить индекс после построения
   vector_store.save()
   ```

4. **Мониторьте производительность**
   ```python
   import time
   start = time.time()
   results = vector_store.search(query)
   print(f"Search took {time.time() - start:.3f}s")
   ```

### Частые ошибки

1. **Забыть активировать venv**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Не установить зависимости**
   ```bash
   pip install -r requirements.txt
   ```

3. **Не создать .env файл**
   ```bash
   cp .env.example .env
   # Отредактировать .env и добавить API ключи
   ```

---

## 🎓 Ресурсы для изучения

### RAG Systems
- [LangChain Documentation](https://python.langchain.com/)
- [LlamaIndex Guide](https://docs.llamaindex.ai/)
- [FAISS Tutorial](https://github.com/facebookresearch/faiss/wiki)

### Evaluation
- [Ragas Framework](https://docs.ragas.io/)
- [BEIR Benchmark](https://github.com/beir-cellar/beir)

### LLM Integration
- [OpenRouter Docs](https://openrouter.ai/docs)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

---

**Последнее обновление**: 2026-02-06  
**Автор**: Руслан Латыпов  
**Проект**: Trading Analytics RAG System
