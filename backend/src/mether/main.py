"""METHER OS Backend — FastAPI application with lifespan management."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from mether.agent.agent import METHERAgent
from mether.agent.llm import LLMClient
from mether.api.routes import router
from mether.api.websocket import websocket_endpoint, voice_ws
from mether.config import Settings, get_settings
from mether.events.bus import EventBus
from mether.memory.context import ContextMemory
from mether.tools.registry import ToolRegistry
from mether.tools.system import SystemTool
from mether.tools.whatsapp import WhatsAppTool, HANDLED_CONTACTS
import asyncio
import time


import logging as _stdlib_logging

_LOG_LEVEL_MAP: dict[str, int] = {
    "DEBUG": _stdlib_logging.DEBUG,
    "INFO": _stdlib_logging.INFO,
    "WARNING": _stdlib_logging.WARNING,
    "ERROR": _stdlib_logging.ERROR,
    "CRITICAL": _stdlib_logging.CRITICAL,
}


def _configure_logging(level: str) -> None:
    """Set up structlog with human-readable console output."""
    numeric_level = _LOG_LEVEL_MAP.get(level.upper(), _stdlib_logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

async def auto_handle_monitor(app: FastAPI):
    """Monitor handled contacts for 10 min inactivity or manual stops to generate summaries."""
    while True:
        await asyncio.sleep(5)
        now = time.time()
        to_remove = []
        for cid, hc in list(HANDLED_CONTACTS.items()):
            if hc.get("stop_requested") or now - hc["last_activity"] > 600: # 10 mins or manually stopped
                to_remove.append(cid)
                
        for cid in to_remove:
            hc = HANDLED_CONTACTS.pop(cid, None)
            if not hc: continue
            
            name = hc["name"]
            duration = int((now - hc["start_time"]) / 60)
            msg_count = len(hc["messages"])
            
            prompt = f"Summarize this WhatsApp conversation between Mayank's AI and {name}. Give: key topics discussed, any important info shared, any action items for Mayank. Keep it bullet points, max 5 bullets.\n\n"
            for m in hc["messages"]:
                speaker = "AI" if m["role"] == "assistant" else name
                prompt += f"{speaker}: {m['content']}\n"
                
            try:
                llm_resp = await app.state.llm.chat(messages=[{"role": "user", "content": prompt}], system="You are a helpful summarizer.")
                content = llm_resp.get("content", [])
                summary = content[0].get("text", "") if content else "Summary failed."
            except Exception:
                summary = "Error generating summary."
                
            await app.state.bus.emit("ws.send", {
                "type": "conversation_summary",
                "contact": name,
                "summary": summary,
                "message_count": msg_count,
                "duration": f"{duration} min"
            })

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    # 1. Load config
    config: Settings = get_settings()

    # 2. Init structured logging
    _configure_logging(config.log_level)
    log = structlog.get_logger("mether.main")

    log.info("startup.begin", version="0.1.0")

    # 3. Init EventBus
    bus = EventBus()

    # 4. Init ContextMemory
    memory = ContextMemory(claude_md_path=config.claude_md_path)
    memory.load_claude_md()

    # 5. Init LLMClient
    llm = LLMClient(config=config)

    # 6. Init ToolRegistry + register built-in tools
    tools = ToolRegistry()
    tools.register(SystemTool())
    tools.register(WhatsAppTool())

    # 7. Init METHERAgent
    agent = METHERAgent(llm=llm, tools=tools, memory=memory, bus=bus)

    # Store everything on app.state for access in routes / ws
    app.state.config = config
    app.state.bus = bus
    app.state.memory = memory
    app.state.llm = llm
    app.state.tools = tools
    app.state.agent = agent
    app.state.ws_client_count = 0

    log.info(
        "startup.complete",
        host=config.mether_host,
        port=config.mether_port,
        tools=tools.list_names(),
    )
    print("\n  ⚡  METHER OS Backend v0.1.0 — ONLINE\n", file=sys.stderr)

    task = asyncio.create_task(auto_handle_monitor(app))

    yield

    task.cancel()
    # ---------- Shutdown ----------
    log.info("shutdown.begin")
    await llm.close()
    log.info("shutdown.complete")


# ======================================================================
# FastAPI application
# ======================================================================

app = FastAPI(
    title="METHER OS",
    description="Personal AI Operating System — Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS (allow the React frontend on :5173) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REST routes ---
app.include_router(router)


# --- WebSocket ---
@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    """WebSocket entry point — delegates to the handler module."""
    await websocket_endpoint(websocket, app.state.agent, app.state.bus)

@app.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket) -> None:
    """WebSocket entry point for voice sidecar."""
    await voice_ws(websocket)


# ======================================================================
# CLI entry point (``python -m mether.main``)
# ======================================================================

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "mether.main:app",
        host=settings.mether_host,
        port=settings.mether_port,
        reload=True,
    )
