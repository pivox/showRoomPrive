from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import load_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    if settings.cron_autostart:
        from src.api.routers.cron import _start_cron
        _start_cron(settings)
    yield


app = FastAPI(title="Showroom Deals Agent", version="2.0.0", lifespan=lifespan)

settings = load_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.routers import ai, cron, products, scan  # noqa: E402

app.include_router(scan.router,     prefix="/scan",     tags=["scan"])
app.include_router(cron.router,     prefix="/cron",     tags=["cron"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(ai.router,       prefix="/ai",       tags=["ai"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    s = load_settings()
    uvicorn.run("src.api.main:app", host=s.api_host, port=s.api_port, reload=True)
