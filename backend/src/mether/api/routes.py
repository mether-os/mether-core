"""REST API routes for METHER OS backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter(tags=["mether"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns OK."""
    return {"status": "ok", "version": "0.1.0"}


@router.get("/status")
async def status(request: Request) -> dict[str, Any]:
    """Readiness / status check with runtime details."""
    tools: list[str] = request.app.state.tools.list_names()
    ws_clients: int = getattr(request.app.state, "ws_client_count", 0)
    return {
        "agent": "ready",
        "tools": tools,
        "ws_clients": ws_clients,
    }


@router.get("/tools")
async def list_tools(request: Request) -> list[dict[str, str]]:
    """Return descriptions of all registered tools."""
    return request.app.state.tools.list_descriptions()
