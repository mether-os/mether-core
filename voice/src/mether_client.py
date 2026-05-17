"""HTTP / WebSocket client for communicating with the METHER backend."""

import asyncio
import json

import httpx
import websockets


class METHERClient:
    """Connects to the METHER OS backend (port 8000) over WebSocket + HTTP."""

    def __init__(self, base_url: str, ws_url: str):
        self.base_url = base_url
        self.ws_url = ws_url
        self.ws = None
        self.msg_queue = asyncio.Queue()
        self.listen_task = None
        self.response_future = None

    async def connect_ws(self):
        """Open a persistent WebSocket to the METHER voice endpoint."""
        self.ws = await websockets.connect(
            self.ws_url,
            ping_interval=20,
            ping_timeout=10,
        )
        self.listen_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        try:
            while True:
                msg = await self.ws.recv()
                data = json.loads(msg)
                if data.get("type") == "voice_response":
                    if self.response_future and not self.response_future.done():
                        self.response_future.set_result(data.get("text", ""))
                else:
                    await self.msg_queue.put(data)
        except Exception:
            pass

    async def send_transcript(self, text: str) -> str:
        """Send a voice transcript and block until the agent responds."""
        self.response_future = asyncio.get_event_loop().create_future()
        await self.ws.send(json.dumps({
            "type": "voice_input",
            "text": text,
        }))
        
        return await asyncio.wait_for(self.response_future, timeout=30)

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
