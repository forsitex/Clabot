import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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


async def scheduled_results_check():
    """
    Funcție NOUĂ pentru verificarea rezultatelor.
    Rulează separat de scheduled_bot_run - NU interferează cu plasarea pariurilor.
    """
    logger.info("Verificare programată rezultate pariuri")

    await broadcast_notification("Verificare rezultate pariuri...", "info")

    result = await bot_engine.check_bet_results()

    await broadcast_bot_state()

    if result["success"]:
        msg = f"Verificare: {result.get('won', 0)} WIN, {result.get('lost', 0)} LOST"
        await broadcast_notification(msg, "success")
    else:
        await broadcast_notification(
            f"Eroare verificare: {result.get('message', 'Eroare necunoscută')}",
            "error"
        )

    logger.info(f"Rezultat verificare: {result}")


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

    # Job NOU pentru verificare rezultate - rulează la fiecare 30 minute
    # ID diferit: "check_results_job" vs "daily_bot_run"
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler.add_job(
        scheduled_results_check,
        trigger=IntervalTrigger(minutes=30),
        id="check_results_job",
        name="Verificare rezultate pariuri",
        replace_existing=True
    )

    scheduler.start()
    logger.info(
        f"Scheduler pornit - Bot programat la {settings.bot_run_hour:02d}:{settings.bot_run_minute:02d} "
        f"({settings.bot_timezone})"
    )
    logger.info("Verificare rezultate programată la fiecare 30 minute")

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


# Serve frontend static files in production
# In Docker: /app/backend/app/main.py -> /app/frontend/dist
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend for all non-API routes."""
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
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
