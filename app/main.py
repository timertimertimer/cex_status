from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from app.collect import get_token_data_from_cache, get_full_data, update_dv_currencies, update_cex_data
from app.config import settings

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await update_dv_currencies()
    await update_cex_data()
    scheduler.add_job(
        update_cex_data,
        trigger=IntervalTrigger(seconds=settings.cex_data_ttl),
        id="update_cex_data_redis",
        replace_existing=True
    )
    scheduler.add_job(
        update_dv_currencies,
        trigger=IntervalTrigger(minutes=5),
        id="update_dv_currencies",
        replace_existing=True
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return await get_full_data()


@app.get("/{token_name}")
async def root(token_name: str):
    data = await get_token_data_from_cache(token_name.upper())
    if not data:
        return {"error": "token not found", "dv_tokens": await update_dv_currencies()}
    return data
