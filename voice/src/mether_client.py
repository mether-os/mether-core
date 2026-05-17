"""HTTP / WebSocket client for communicating with the METHER backend."""

import json

import httpx
import websockets


class METHERClient:
    """Connects to the METHER OS backend (port 8000) over WebSocket + HTTP."""

    def __init__(self, base_url: str, ws_url: str):
        self.base_url = base_url
        self.ws_url = ws_url
        self.ws = None

    async def connect_ws(self):
        """Open a persistent WebSocket to the METHER voice endpoint."""
        self.ws = await websockets.connect(
            self.ws_url,
            ping_interval=20,
            ping_timeout=10,
        )

    async def send_transcript(self, text: str) -> str:
        """Send a voice transcript and block until the agent responds."""
        await self.ws.send(json.dumps({
            "type": "voice_input",
            "text": text,
        }))

        # Wait for the agent's voice_response (skip other event types)
        import asyncio
        while True:
            msg = await asyncio.wait_for(self.ws.recv(), timeout=30)
            data = json.loads(msg)
            if data.get("type") == "voice_response":
                return data.get("text", "")

    async def notify(self, event: str, data: dict):
        """Fire-and-forget event notification to the backend."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.base_url}/voice/event",
                    json={"event": event, "data": data},
                    timeout=3,
                )
        except Exception:
            pass  # best-effort, never block the voice loop
