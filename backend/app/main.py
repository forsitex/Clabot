import logging
from contextlib import asynccontextmanager
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.websocket import websocket_endpoint, broadcast_bot_state, broadcast_notification
from app.config import get_settings
from app.services.bot_engine import bot_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()
scheduler = AsyncIOScheduler()


async def scheduled_bot_run():
    """Funcție executată de scheduler la ora configurată."""
    logger.info("Execuție programată a botului")

    await broadcast_notification("Botul începe execuția programată", "info")

    result = await bot_engine.run_cycle()

    await broadcast_bot_state()

    if result["success"]:
        await broadcast_notification(
            f"Ciclu complet: {result.get('bets_placed', 0)} pariuri plasate",
            "success"
        )
    else:
        await broadcast_notification(
            f"Eroare: {result.get('message', 'Eroare necunoscută')}",
            "error"
        )

    logger.info(f"Rezultat execuție programată: {result}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager pentru aplicație."""
    logger.info("Pornire aplicație...")

    timezone = pytz.timezone(settings.bot_timezone)
    trigger = CronTrigger(
        hour=settings.bot_run_hour,
        minute=settings.bot_run_minute,
        timezone=timezone
    )

    scheduler.add_job(
        scheduled_bot_run,
        trigger=trigger,
        id="daily_bot_run",
        name="Execuție zilnică bot",
        replace_existing=True
    )

    scheduler.start()
    logger.info(
        f"Scheduler pornit - Bot programat la {settings.bot_run_hour:02d}:{settings.bot_run_minute:02d} "
        f"({settings.bot_timezone})"
    )

    yield

    logger.info("Oprire aplicație...")
    scheduler.shutdown()
    logger.info("Scheduler oprit")


app = FastAPI(
    title="Betfair Bot API",
    description="API pentru botul de pariuri Betfair Exchange",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

app.add_api_websocket_route("/ws", websocket_endpoint)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Betfair Bot API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "scheduled_run": f"{settings.bot_run_hour:02d}:{settings.bot_run_minute:02d} {settings.bot_timezone}"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
