import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from llm_cache_router import CacheConfig, LLMRouter, RoutingStrategy

DEFAULT_MODEL = "MiniMax-M2.5"


def load_dotenv_file(env_path: str = ".env") -> None:
    env_file = Path(env_path)
    if not env_file.is_absolute():
        env_file = Path(__file__).resolve().with_name(env_path)
    if not env_file.exists():
        return

    # Загружаем только отсутствующие переменные, чтобы не перетирать уже заданные в окружении.
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


class ChatMessage(BaseModel):
    role: str = Field(description="Роль сообщения: system/user/assistant")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None


class ChatResponse(BaseModel):
    content: str
    provider_used: str
    model_used: str
    cache_hit: bool
    cost_usd: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv_file()

    minimax_api_key = os.getenv("MINIMAX_API_KEY")
    if not minimax_api_key:
        raise RuntimeError("Укажи переменную окружения MINIMAX_API_KEY")
    minimax_base_url = os.getenv("MINIMAX_API_BASE_URL")
    if minimax_base_url:
        minimax_base_url = minimax_base_url.rstrip("/")
        if not minimax_base_url.endswith("/v1"):
            minimax_base_url = f"{minimax_base_url}/v1"
    minimax_model = os.getenv("MINIMAX_MODEL", DEFAULT_MODEL)
    app.state.default_model = minimax_model

    # Инициализируем роутер один раз на всё приложение.
    app.state.llm_router = LLMRouter(
        providers={
            "minimax": {
                "api_key": minimax_api_key,
                "base_url": minimax_base_url,
                "models": [minimax_model],
            },
        },
        cache=CacheConfig(
            backend="memory",
            threshold=0.92,
            ttl=3600,
            max_entries=10_000,
        ),
        strategy=RoutingStrategy.CHEAPEST_FIRST,
        budget={"daily_usd": 3.0, "monthly_usd": 30.0},
    )
    try:
        yield
    finally:
        await app.state.llm_router.close()


app = FastAPI(
    title="llm-cache-router + FastAPI example",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    router: LLMRouter = app.state.llm_router
    model_to_use: str = payload.model or app.state.default_model
    try:
        response = await router.complete(
            messages=[message.model_dump() for message in payload.messages],
            model=model_to_use,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ошибка провайдера: {exc}") from exc

    return ChatResponse(
        content=response.content,
        provider_used=response.provider_used,
        model_used=response.model_used,
        cache_hit=response.cache_hit,
        cost_usd=response.cost_usd,
    )


@app.get("/stats")
async def stats() -> dict:
    router: LLMRouter = app.state.llm_router
    return router.stats().model_dump()


# Запуск:
# uvicorn main:app --reload
