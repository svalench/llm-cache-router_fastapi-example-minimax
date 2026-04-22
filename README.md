# llm-cache-router: basic FastAPI example

This repository is a minimal integration example for the core [`llm-cache-router`](https://github.com/svalench/llm-cache-router) library with FastAPI and the MiniMax provider.

The goal is to provide a practical starter template that you can quickly adapt for your own service.

## What this example demonstrates

- initializing `LLMRouter` in the FastAPI app lifecycle;
- configuring and using the `minimax` provider;
- in-memory semantic cache (`CacheConfig(backend="memory")`);
- basic budget limits (`daily_usd`, `monthly_usd`);
- `POST /chat` endpoint for completions;
- `GET /stats` endpoint for router metrics.

## Files

- `main.py` — ready-to-run FastAPI app with endpoints and `llm-cache-router` config.

## Requirements

- Python 3.11+
- `pip`

Install dependencies:

```bash
pip install llm-cache-router fastapi uvicorn
```

## .env configuration

Create a `.env` file next to `main.py`:

```env
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_API_BASE_URL=https://api.minimax.io
MINIMAX_MODEL=MiniMax-M2.5
```

Notes:

- `MINIMAX_API_KEY` is required.
- `MINIMAX_API_BASE_URL` is optional (if `/v1` is missing, the app appends it automatically).
- `MINIMAX_MODEL` is optional; otherwise the default from `main.py` is used.

## Run

```bash
uvicorn main:app --reload
```

After startup, the API is available at `http://127.0.0.1:8000`.

## Request examples

### 1) Chat request

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Briefly explain what semantic caching is"}
    ]
  }'
```

### 2) Router stats

```bash
curl "http://127.0.0.1:8000/stats"
```

## How to verify cache behavior

Send the same request to `POST /chat` twice in a row.  
On the second request, you should typically see `cache_hit: true` and near-zero cost.

---

As a next step, you can add a streaming endpoint (`/chat/stream`) via `router.stream(...)`.
