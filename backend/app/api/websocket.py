import asyncio
import json
import logging
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from app.services.bot_engine import bot_engine

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manager pentru conexiuni WebSocket."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Acceptă o conexiune nouă."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client conectat. Total conexiuni: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Elimină o conexiune."""
        self.active_connections.discard(websocket)
        logger.info(f"Client deconectat. Total conexiuni: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Trimite un mesaj către toți clienții conectați."""
        if not self.active_connections:
            return

        message_json = json.dumps(message, default=str)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Eroare trimitere mesaj: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Trimite un mesaj către un client specific."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.warning(f"Eroare trimitere mesaj personal: {e}")


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket pentru actualizări în timp real."""
    await manager.connect(websocket)

    try:
        state = bot_engine.get_state()
        stats = bot_engine.get_dashboard_stats()
        await manager.send_personal(websocket, {
            "type": "initial_state",
            "data": {
                "bot_state": state.model_dump(),
                "stats": stats.model_dump()
            },
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                message = json.loads(data)
                await handle_websocket_message(websocket, message)

            except asyncio.TimeoutError:
                await manager.send_personal(websocket, {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Eroare WebSocket: {e}")
        manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, message: dict):
    """Procesează mesajele primite de la client."""
    msg_type = message.get("type")

    if msg_type == "pong":
        return

    elif msg_type == "get_state":
        state = bot_engine.get_state()
        await manager.send_personal(websocket, {
            "type": "bot_state",
            "data": state.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })

    elif msg_type == "get_stats":
        stats = bot_engine.get_dashboard_stats()
        await manager.send_personal(websocket, {
            "type": "stats",
            "data": stats.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })

    elif msg_type == "get_teams":
        teams = bot_engine.get_all_teams()
        await manager.send_personal(websocket, {
            "type": "teams",
            "data": [t.model_dump() for t in teams],
            "timestamp": datetime.utcnow().isoformat()
        })

    elif msg_type == "get_bets":
        bets = bot_engine.get_all_bets()
        await manager.send_personal(websocket, {
            "type": "bets",
            "data": [b.model_dump() for b in bets],
            "timestamp": datetime.utcnow().isoformat()
        })

    else:
        await manager.send_personal(websocket, {
            "type": "error",
            "message": f"Tip mesaj necunoscut: {msg_type}",
            "timestamp": datetime.utcnow().isoformat()
        })


async def broadcast_bot_state():
    """Broadcast starea botului către toți clienții."""
    state = bot_engine.get_state()
    await manager.broadcast({
        "type": "bot_state",
        "data": state.model_dump(),
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_stats():
    """Broadcast statisticile către toți clienții."""
    stats = bot_engine.get_dashboard_stats()
    await manager.broadcast({
        "type": "stats",
        "data": stats.model_dump(),
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_bet_update(bet_id: str):
    """Broadcast actualizare pariu."""
    bet = bot_engine.get_bet(bet_id)
    if bet:
        await manager.broadcast({
            "type": "bet_update",
            "data": bet.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })


async def broadcast_team_update(team_id: str):
    """Broadcast actualizare echipă."""
    team = bot_engine.get_team(team_id)
    if team:
        await manager.broadcast({
            "type": "team_update",
            "data": team.model_dump(),
            "timestamp": datetime.utcnow().isoformat()
        })


async def broadcast_notification(message: str, level: str = "info"):
    """Broadcast notificare."""
    await manager.broadcast({
        "type": "notification",
        "data": {
            "message": message,
            "level": level
        },
        "timestamp": datetime.utcnow().isoformat()
    })


# Logs WebSocket Manager
logs_manager = ConnectionManager()


async def logs_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint pentru streaming logs în timp real."""
    await logs_manager.connect(websocket)

    try:
        # Stream logs from journalctl
        import subprocess

        process = subprocess.Popen(
            ["journalctl", "-u", "betfair-bot", "-f", "--no-pager"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        while True:
            line = process.stdout.readline()
            if line:
                await websocket.send_text(line.strip())

            # Check if websocket is still connected
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            except:
                break

    except WebSocketDisconnect:
        logs_manager.disconnect(websocket)
        if 'process' in locals():
            process.kill()
    except Exception as e:
        logger.error(f"Eroare Logs WebSocket: {e}")
        logs_manager.disconnect(websocket)
        if 'process' in locals():
            process.kill()
