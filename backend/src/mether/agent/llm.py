"""Async LLM client — talks to the free-claude-code proxy."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from mether.config import Settings

logger = structlog.get_logger(__name__)

# Timeout for a single LLM round-trip.
_LLM_TIMEOUT = 30.0


class LLMClient:
    """Thin async wrapper around the Anthropic-compatible ``/v1/messages`` endpoint.

    The client posts to the *free-claude-code* proxy (by default on
    ``http://localhost:8082``) using the Anthropic messages format.
    """

    def __init__(self, config: Settings) -> None:
        self._base_url = config.llm_proxy_url.rstrip("/")
        self._model = config.llm_model
        self._auth_token = config.anthropic_auth_token
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(_LLM_TIMEOUT),
            headers={
                "x-api-key": self._auth_token,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the parsed response.

        Parameters
        ----------
        messages:
            Anthropic-format message list (``role`` + ``content``).
        tools:
            Optional list of tool schemas for tool-calling.
        system:
            Optional system prompt string.

        Returns
        -------
        dict
            The full JSON response from the proxy.

        Raises
        ------
        LLMError
            On network failure, timeout, or non-2xx status.
        """
        url = f"{self._base_url}/v1/messages"

        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": messages,
            "stream": False,
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = tools

        logger.debug("llm.request", url=url, model=self._model, msg_count=len(messages))

        try:
            resp = await self._client.post(url, json=body)
            resp.raise_for_status()
            
            content_type = resp.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                data = self._parse_sse_response(resp.text)
                logger.debug("llm.response_sse_parsed", stop_reason=data.get("stop_reason"))
                return data
            else:
                data = resp.json()
                logger.debug("llm.response", stop_reason=data.get("stop_reason"))
                return data

        except httpx.TimeoutException as exc:
            logger.error("llm.timeout", url=url, detail=str(exc))
            raise LLMError(f"LLM request timed out after {_LLM_TIMEOUT}s") from exc

        except httpx.HTTPStatusError as exc:
            logger.error(
                "llm.http_error",
                status=exc.response.status_code,
                body=exc.response.text[:500],
            )
            raise LLMError(
                f"LLM proxy returned {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc

        except httpx.HTTPError as exc:
            logger.error("llm.network_error", detail=str(exc))
            raise LLMError(f"LLM proxy unreachable: {exc}") from exc

    def _parse_sse_response(self, text: str) -> dict[str, Any]:
        """Parse Anthropic SSE format into a standard message dict."""
        import json
        
        final_message: dict[str, Any] = {
            "id": "",
            "type": "message",
            "role": "assistant",
            "model": self._model,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {}
        }
        
        current_block = None
        
        for line in text.splitlines():
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                    
                try:
                    event = json.loads(data_str)
                    event_type = event.get("type")
                    
                    if event_type == "message_start":
                        final_message["id"] = event["message"].get("id", "")
                        final_message["usage"] = event["message"].get("usage", {})
                        
                    elif event_type == "content_block_start":
                        block = event["content_block"]
                        if block["type"] == "tool_use":
                            block["input"] = "" 
                        current_block = block
                        final_message["content"].append(current_block)
                        
                    elif event_type == "content_block_delta":
                        delta = event["delta"]
                        if current_block:
                            if delta["type"] == "text_delta":
                                current_block["text"] = current_block.get("text", "") + delta.get("text", "")
                            elif delta["type"] == "input_json_delta":
                                current_block["input"] += delta.get("partial_json", "")
                                
                    elif event_type == "content_block_stop":
                        if current_block and current_block["type"] == "tool_use":
                            if isinstance(current_block["input"], str):
                                try:
                                    current_block["input"] = json.loads(current_block["input"] or "{}")
                                except json.JSONDecodeError:
                                    current_block["input"] = {}
                        current_block = None
                        
                    elif event_type == "message_delta":
                        if "stop_reason" in event["delta"]:
                            final_message["stop_reason"] = event["delta"]["stop_reason"]
                            
                except json.JSONDecodeError:
                    pass

        return final_message

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Shut down the underlying httpx client."""
        await self._client.aclose()


class LLMError(Exception):
    """Raised when the LLM proxy call fails for any reason."""
