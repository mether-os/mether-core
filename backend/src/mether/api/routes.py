"""REST API routes for METHER OS backend."""

from __future__ import annotations

from typing import Any, Optional, List, Dict
from pydantic import BaseModel

from fastapi import APIRouter, Request, Header, HTTPException, Depends
import httpx
import asyncio
import structlog
import time
from mether.tools.whatsapp import HANDLED_CONTACTS
from mether.config import get_settings

async def verify_api_key(x_mether_key: str | None = Header(None, alias="X-METHER-KEY")) -> None:
    settings = get_settings()
    if settings.mether_api_key and x_mether_key != settings.mether_api_key:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid or missing API key")

router = APIRouter(tags=["mether"], prefix="/api/v1", dependencies=[Depends(verify_api_key)])
root_router = APIRouter(tags=["health"])


def _enforce_alternating_roles(messages: list[dict]) -> list[dict]:
    """Ensure messages follow the strict user/assistant alternating pattern.

    1. Merge consecutive messages from the same role by joining content.
    2. Drop leading assistant messages so the list always starts with 'user'.
    """
    if not messages:
        return messages

    # Step 1: merge consecutive same-role messages
    merged: list[dict] = []
    for msg in messages:
        if merged and merged[-1]["role"] == msg["role"]:
            # Append content with a newline separator
            merged[-1]["content"] = merged[-1]["content"] + "\n" + msg["content"]
        else:
            merged.append({"role": msg["role"], "content": msg["content"]})

    # Step 2: drop leading assistant messages
    while merged and merged[0]["role"] != "user":
        merged.pop(0)

    return merged


async def load_google_from_env():
    """Load Google credentials from env vars on Render."""
    import os
    from pathlib import Path
    from mether.config import get_settings
    settings = get_settings()
    
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    claude_md = os.getenv("CLAUDE_MD_CONTENT")
    
    to_write = []
    if creds_json:
        to_write.append((Path(settings.google_credentials_path).expanduser().resolve(), creds_json))
    if token_json:
        to_write.append((Path(settings.google_token_path).expanduser().resolve(), token_json))
    if claude_md:
        to_write.append((Path(settings.claude_md_path).expanduser().resolve(), claude_md))
        
    for path, content in to_write:
        parent = path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
            try:
                parent.chmod(0o700)
            except Exception:
                pass
        
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
        path.write_text(content, encoding="utf-8")
        try:
            path.chmod(0o600)
        except Exception:
            pass

@root_router.get("/health")
@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    """Liveness probe — always returns OK."""
    from mether.config import get_settings
    config = get_settings()
    
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": config.environment,
        "services": {
            "llm_proxy": "connected" if config.llm_proxy_url else "unreachable",
            "google": "configured" if config.google_client_id else "not_configured",
            "whatsapp": "connected"
        }
    }


@router.get("/status")
async def status(request: Request) -> dict[str, Any]:
    """Readiness / status check with runtime details."""
    tools: list[str] = request.app.state.tools.list_names()
    ws_clients: int = getattr(request.app.state, "ws_client_count", 0)
    # Expose the active model name so the frontend HUD can display it dynamically
    config = request.app.state.config
    model_name: str = getattr(config, "llm_model", "claude-sonnet-4-5")
    return {
        "agent": "ready",
        "tools": tools,
        "ws_clients": ws_clients,
        "model": model_name,
    }


@router.get("/tools")
async def list_tools(request: Request) -> list[dict[str, str]]:
    """Return descriptions of all registered tools."""
    return request.app.state.tools.list_descriptions()


@router.post("/whatsapp/event")
async def whatsapp_event(request: Request):
    """Receive events from the WhatsApp Node.js sidecar."""
    logger = structlog.get_logger(__name__)
    bus = request.app.state.bus
    
    body = await request.json()
    event = body.get("event")
    data = body.get("data", {})
    
    if event == "whatsapp.message":
        from mether.services.whatsapp_handler import handle_incoming_whatsapp_message
        asyncio.create_task(handle_incoming_whatsapp_message(data, request.app.state.llm, bus))
    
    elif event == "whatsapp.ready":
        logger.info("whatsapp.ready", status="connected")
        await bus.emit("ws.send", {"type": "whatsapp_status", "status": "connected"})
        await bus.emit("ws.send", {"type": "log", "module": "WA", "message": "WhatsApp connected"})
        
    elif event == "whatsapp.qr":
        qr_data = data.get("qr")
        await bus.emit("ws.send", {"type": "whatsapp_qr", "qr": qr_data})
        await bus.emit("ws.send", {"type": "whatsapp_status", "status": "disconnected"})
        await bus.emit("ws.send", {"type": "log", "module": "WA", "message": "New QR code generated"})
        
    elif event == "whatsapp.disconnected":
        logger.warning("whatsapp.disconnected", reason=data.get("reason"))
        await bus.emit("ws.send", {"type": "whatsapp_status", "status": "disconnected"})
        await bus.emit("ws.send", {"type": "log", "module": "WA", "message": f"Disconnected: {data.get('reason')}"})

    return {"success": True}

@router.get("/whatsapp/handled")
async def get_handled():
    """Return currently handled contacts."""
    return HANDLED_CONTACTS

@router.get("/whatsapp/status")
async def whatsapp_status():
    """Proxy status check to the WhatsApp sidecar."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:3001/status")
            return resp.json()
    except httpx.HTTPError as e:
        return {"status": "disconnected", "error": str(e)}

@router.post("/voice/event")
async def voice_event(request: Request):
    """Receive lifecycle events from the voice sidecar."""
    logger = structlog.get_logger(__name__)
    bus = request.app.state.bus
    
    body = await request.json()
    event = body.get("event")
    data = body.get("data", {})
    
    if event == "voice.online":
        logger.info("[VOICE] Pipeline online")
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": "Pipeline online"})
        await bus.emit("ws.send", {"type": "voice_status", "status": "online"})
        
    elif event == "voice.offline":
        logger.info("[VOICE] Pipeline offline")
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": "Pipeline offline"})
        await bus.emit("ws.send", {"type": "voice_status", "status": "offline"})
        
    elif event == "voice.wake":
        logger.info("[VOICE] Wake word detected")
        await bus.emit("ws.send", {"type": "orb_state", "state": "listening"})
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": "Wake word detected"})
        
    elif event == "voice.transcript":
        text = data.get("text", "")
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": f"Heard: {text}"})
        
    elif event == "voice.speaking":
        await bus.emit("ws.send", {"type": "orb_state", "state": "speaking"})
        
    elif event == "voice.done":
        await bus.emit("ws.send", {"type": "orb_state", "state": "idle"})
        
    return {"success": True}

@router.get("/google/status")
async def google_status(request: Request) -> dict[str, Any]:
    auth = request.app.state.google_auth
    if not auth.is_authenticated():
        return {"authenticated": False}
    
    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=auth.get_credentials())
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")
    except Exception:
        email = None
        
    return {
        "authenticated": True,
        "email": email,
        "scopes": getattr(auth.get_credentials(), "scopes", []),
        "token_expires": str(getattr(auth.get_credentials(), "expiry", None))
    }

@router.get("/google/auth/url")
async def google_auth_url(request: Request) -> dict[str, Any]:
    auth = request.app.state.google_auth
    if not auth.credentials_path.exists():
        return {"error": "Google client credentials file missing on backend"}
    
    redirect_uri = str(request.url_for("google_auth_callback"))
    try:
        url = auth.get_authorization_url(redirect_uri)
        return {"url": url}
    except Exception as e:
        return {"error": str(e)}

@root_router.get("/api/v1/google/auth/callback", name="google_auth_callback")
async def google_auth_callback(request: Request, code: str) -> Any:
    from fastapi.responses import RedirectResponse
    auth = request.app.state.google_auth
    redirect_uri = str(request.url_for("google_auth_callback"))
    try:
        await asyncio.to_thread(auth.fetch_token_from_code, code, redirect_uri)
        config = request.app.state.config
        return RedirectResponse(url=config.frontend_url)
    except Exception as e:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=f"<h3>Authentication Failed</h3><p>{e}</p>", status_code=400)

@router.get("/google/logout")
async def google_logout(request: Request) -> dict[str, Any]:
    auth = request.app.state.google_auth
    if auth.token_path.exists():
        auth.token_path.unlink()
    return {"logged_out": True}

@router.get("/vitals")
async def get_vitals() -> dict[str, Any]:
    """Get real-time system metrics (CPU, RAM, disk, processes, uptime)."""
    import psutil
    mem = psutil.virtual_memory()
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": mem.percent,
        "disk": psutil.disk_usage('/').percent,
        "processes": len(psutil.pids()),
        "uptime": int(time.time() - psutil.boot_time())
    }

@router.get("/objectives")
async def get_objectives(request: Request) -> dict[str, Any]:
    """Parse CLAUDE.md to extract objectives dynamically."""
    import re
    from pathlib import Path
    config = request.app.state.config
    claude_md_path = Path(config.claude_md_path).expanduser().resolve()
    
    objectives = []
    if claude_md_path.is_file():
        try:
            content = claude_md_path.read_text(encoding="utf-8")
            focus_match = re.search(r"## CURRENT FOCUS.*?\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
            if focus_match:
                lines = focus_match.group(1).strip().split("\n")
                for line in lines:
                    line = line.strip()
                    m = re.match(r"^(?:\d+\.|\-)\s*(.*)$", line)
                    if m:
                        name = m.group(1).strip()
                        progress = 0
                        status = "PENDING"
                        if "mether" in name.lower():
                            progress = 85
                            status = "IN PROGRESS"
                        elif "dsa" in name.lower() or "leetcode" in name.lower():
                            progress = 50
                            status = "IN PROGRESS"
                        elif "internship" in name.lower() or "freelance" in name.lower():
                            progress = 20
                            status = "IN PROGRESS"
                        objectives.append({
                            "name": name.upper(),
                            "progress": progress,
                            "status": status
                        })
        except Exception:
            pass
            
    if not objectives:
        objectives = [
            { "name": "SHIP METHER OS V1.0", "progress": 85, "status": "IN PROGRESS" },
            { "name": "LAND INTERNSHIP / FREELANCE", "progress": 20, "status": "IN PROGRESS" },
            { "name": "DSA CONSISTENCY ON LEETCODE", "progress": 50, "status": "IN PROGRESS" },
        ]
        
    return {"objectives": objectives}

@router.post("/memory/reload")
async def reload_memory(request: Request) -> dict[str, Any]:
    """Reload CLAUDE.md memory persona from disk."""
    request.app.state.memory.reload()
    return {"success": True, "message": "CLAUDE.md persona reloaded successfully"}

# ------------------------------------------------------------------
# Research Pipeline REST API
# ------------------------------------------------------------------
# Research Pipeline REST API
class ResearchStartRequest(BaseModel):
    topic: str
    depth: str = "deep"
    length_target: str = "20_pages"
    scope: str = "web_local"
    template: str = "research_report"
    format: str = "Markdown"
    model_routing: dict[str, str] = {}
    research_mode: str = "balanced"
    target_audience: str = "researcher"
    human_review_enabled: int = 0

class OutlineApproveRequest(BaseModel):
    modified_sections: list[dict[str, Any]] = []

class SectionRegenRequest(BaseModel):
    instructions: str

class DeliveryRequest(BaseModel):
    format: str
    template: str
    delivery_channel: str = "local_save"
    destination: str = ""

class HumanReviewSubmitRequest(BaseModel):
    decision: str
    notes: Optional[str] = ""

class OutcomeRecordRequest(BaseModel):
    actual_outcome: str
    user_feedback: Optional[str] = ""
    correct: bool

class FeedbackRequest(BaseModel):
    user_feedback: str

@router.post("/research")
async def start_research(request: Request, body: ResearchStartRequest) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    routing = body.model_routing or {
        "planner": "nvidia_nim/z-ai/glm4.7",
        "researcher": "nvidia_nim/z-ai/glm4.7",
        "writer": "nvidia_nim/z-ai/glm4.7",
        "reviewer": "nvidia_nim/z-ai/glm4.7"
    }
    
    task_id = await orch.create_task(
        body.topic, body.depth, body.length_target, body.scope, body.template, routing,
        body.research_mode, body.target_audience, body.human_review_enabled
    )
    # Set format requested
    await orch.db._run_query(
        "UPDATE research_tasks SET format_requested = ? WHERE id = ?",
        body.format, task_id, is_write=True
    )
    
    await orch.enqueue(task_id)
    return {"task_id": task_id, "status": "queued"}

@router.get("/research")
async def list_research_tasks(request: Request) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    tasks = await orch.db._run_query("SELECT * FROM research_tasks ORDER BY created_at DESC")
    return [dict(t) for t in tasks]

@router.get("/research/{task_id}")
async def get_research_status(request: Request, task_id: str) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    task = await orch.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    sections = await orch.get_sections(task_id)
    sources = await orch.db._run_query("SELECT url, title, credibility_score, trust_score, source_type FROM research_sources WHERE task_id = ?", task_id)
    
    return {
        "task": task,
        "sections": sections,
        "sources": sources
    }

@router.get("/research/{task_id}/claims")
async def get_task_claims(request: Request, task_id: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    claims = await orch.db._run_query("SELECT * FROM research_claims WHERE task_id = ?", task_id)
    return [dict(c) for c in claims]

@router.get("/research/{task_id}/claims/{claim_id}")
async def get_task_claim(request: Request, task_id: str, claim_id: int) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    claim = await orch.db._run_query("SELECT * FROM research_claims WHERE id = ? AND task_id = ?", claim_id, task_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return dict(claim[0])

@router.get("/research/{task_id}/evidence-vault")
async def get_task_evidence_vault(request: Request, task_id: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    vault = await orch.db._run_query("SELECT * FROM evidence_vault WHERE task_id = ?", task_id)
    return [dict(v) for v in vault]

@router.get("/research/{task_id}/evidence-vault/{vault_id}")
async def get_task_evidence_snapshot(request: Request, task_id: str, vault_id: int) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    snapshot = await orch.db._run_query("SELECT * FROM evidence_vault WHERE id = ? AND task_id = ?", vault_id, task_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return dict(snapshot[0])

@router.get("/research/{task_id}/contradictions")
async def get_task_contradictions(request: Request, task_id: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    contras = await orch.db._run_query("SELECT * FROM research_contradictions WHERE task_id = ?", task_id)
    return [dict(c) for c in contras]

@router.get("/research/{task_id}/unknowns")
async def get_task_unknowns(request: Request, task_id: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    unknowns = await orch.db._run_query("SELECT * FROM research_claims WHERE task_id = ? AND verification_status = 'Unverified'", task_id)
    return [dict(u) for u in unknowns]

@router.get("/research/{task_id}/independence")
async def get_task_independence(request: Request, task_id: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    ind = await orch.db._run_query("SELECT * FROM source_independence WHERE task_id = ?", task_id)
    return [dict(i) for i in ind]

@router.get("/research/{task_id}/source-network")
async def get_task_source_network(request: Request, task_id: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    net = await orch.db._run_query("SELECT * FROM source_network WHERE task_id = ?", task_id)
    return [dict(n) for n in net]

@router.get("/research/{task_id}/devils-advocate")
async def get_task_devils_advocate(request: Request, task_id: str) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    da = await orch.db._run_query("SELECT * FROM devils_advocate WHERE task_id = ?", task_id)
    if not da:
        raise HTTPException(status_code=404, detail="Devil's Advocate report not found")
    res = dict(da[0])
    try:
        return {
            "task_id": task_id,
            "counter_arguments": json.loads(res["counter_arguments_json"]),
            "alternative_interpretations": json.loads(res["alternative_interpretations_json"]),
            "confidence_risks": json.loads(res["confidence_risks_json"]),
            "why_wrong": json.loads(res["why_wrong_json"])
        }
    except Exception:
        return {}

@router.get("/research/{task_id}/decision")
async def get_task_decision_brief(request: Request, task_id: str) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    res = await orch.db._run_query("SELECT * FROM decision_layer WHERE task_id = ?", task_id)
    if not res:
        raise HTTPException(status_code=404, detail="Decision brief not found")
    r = dict(res[0])
    try:
        return {
            "task_id": task_id,
            "key_findings": json.loads(r["key_findings"]),
            "green_flags": json.loads(r["green_flags"]),
            "red_flags": json.loads(r["red_flags"]),
            "open_questions": json.loads(r["open_questions"]),
            "risks": json.loads(r["risks"]),
            "opportunities": json.loads(r["opportunities"]),
            "decision_summary": r["decision_summary"],
            "confidence_level": r["confidence_level"],
            "target_audience": r["target_audience"],
            "devils_advocate_summary": r["devils_advocate_summary"],
            "research_failure": r["research_failure"],
            "failure_reason": r["failure_reason"]
        }
    except Exception:
        return {}

@router.get("/research/{task_id}/action-plan")
async def get_task_action_plan(request: Request, task_id: str) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    res = await orch.db._run_query("SELECT * FROM research_action_plans WHERE task_id = ?", task_id)
    if not res:
        raise HTTPException(status_code=404, detail="Action plan not found")
    r = dict(res[0])
    try:
        return {
            "task_id": task_id,
            "actions": json.loads(r["actions_json"]),
            "next_steps": json.loads(r["next_steps_json"]),
            "quick_wins": json.loads(r["quick_wins_json"]),
            "long_term_actions": json.loads(r["long_term_actions_json"])
        }
    except Exception:
        return {}

@router.get("/research/{task_id}/change-report")
async def get_task_change_report(request: Request, task_id: str) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    task = await orch.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    topic_hash = orch._get_topic_hash(task["topic"])
    history = await orch.db._run_query(
        "SELECT * FROM research_history WHERE topic_hash = ? AND task_id != ? ORDER BY id DESC LIMIT 1",
        topic_hash, task_id
    )
    if not history:
        return {"change_report": "First-time research run. No historical comparison available."}
        
    new_claims = await orch.db._run_query("SELECT * FROM research_claims WHERE task_id = ?", task_id)
    old_snap = json.loads(history[0]["snapshot_json"])
    report_md = await orch._generate_change_report(old_snap, [dict(c) for c in new_claims])
    return {"change_report": report_md}

@router.get("/research/{task_id}/human-review")
async def get_task_human_review_queue(request: Request, task_id: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    queue = await orch.db._run_query("SELECT * FROM human_review_queue WHERE task_id = ?", task_id)
    return [dict(q) for q in queue]

@router.post("/research/{task_id}/human-review/{item_id}")
async def submit_human_review(request: Request, task_id: str, item_id: int, body: HumanReviewSubmitRequest) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    from mether.services.research.human_review import HumanReviewGate
    hr_gate = HumanReviewGate(orch.db)
    
    await hr_gate.submit_review(item_id, body.decision, body.notes or "")
    
    # If all reviews completed, resume execution
    if await hr_gate.is_review_complete(task_id):
        await orch.update_task_status(task_id, "queued", "writing") # resume to writing stage
        await orch.enqueue(task_id)
        return {"success": True, "resumed": True, "message": "All reviews complete. Research pipeline resumed."}
        
    return {"success": True, "resumed": False, "message": "Review submitted. Waiting for remaining reviews."}

@router.get("/research/history/{topic_hash}")
async def get_research_history_snapshots(request: Request, topic_hash: str) -> list[dict[str, Any]]:
    orch = request.app.state.research_orchestrator
    hist = await orch.db._run_query("SELECT id, task_id, created_at FROM research_history WHERE topic_hash = ? ORDER BY id DESC", topic_hash)
    return [dict(h) for h in hist]

@router.get("/research/accuracy")
async def get_global_accuracy_metrics(request: Request) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    from mether.services.research.accuracy_metrics import AccuracyMetricsEngine
    metrics_engine = AccuracyMetricsEngine(orch.db)
    
    metrics = await metrics_engine.compute_metrics()
    history = await metrics_engine.get_metrics_history(limit=10)
    return {
        "latest": metrics,
        "history": history
    }

@router.post("/research/{task_id}/outcomes/{rec_id}")
async def record_recommendation_outcome(request: Request, task_id: str, rec_id: int, body: OutcomeRecordRequest) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    from mether.services.research.outcome_tracker import OutcomeTrackerAgent
    tracker = OutcomeTrackerAgent(orch.db)
    
    await tracker.record_outcome(rec_id, body.actual_outcome, body.user_feedback, body.correct)
    return {"success": True, "message": "Recommendation outcome recorded."}

@router.post("/research/{task_id}/outcomes/{rec_id}/feedback")
async def submit_recommendation_feedback(request: Request, task_id: str, rec_id: int, body: FeedbackRequest) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    await orch.db._run_query(
        "UPDATE recommendation_outcomes SET user_feedback = ? WHERE id = ? AND task_id = ?",
        body.user_feedback, rec_id, task_id, is_write=True
    )
    return {"success": True, "message": "Feedback submitted."}

@router.post("/research/{task_id}/outline/approve")
async def approve_outline(request: Request, task_id: str, body: OutlineApproveRequest) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    task = await orch.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Delete old outline sections
    await orch.db._run_query("DELETE FROM research_sections WHERE task_id = ?", task_id, is_write=True)
    
    # Save the modified outline
    for idx, item in enumerate(body.modified_sections):
        await orch.add_section(task_id, item["title"], idx + 1, item.get("instructions", ""))
        
    # Set stage to collecting and status to queued, then enqueue to resume
    await orch.update_task_status(task_id, "queued", "collecting")
    await orch.enqueue(task_id)
    
    return {"success": True, "message": "Outline approved. Research resumes."}

@router.post("/research/{task_id}/sections/{section_id}/regenerate")
async def regenerate_section(request: Request, task_id: str, section_id: int, body: SectionRegenRequest) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    sec = await orch.get_section(section_id)
    if not sec:
        raise HTTPException(status_code=404, detail="Section not found")
        
    # Set status to pending
    await orch.update_section_content(section_id, "pending")
    
    # Custom instructions overrides section instructions
    updated_instructions = f"{sec.get('instructions', '')} // REGENERATE INSTRUCTIONS: {body.instructions}"
    await orch.db._run_query("UPDATE research_sections SET instructions = ? WHERE id = ?", updated_instructions, section_id, is_write=True)
    
    # Run writer & reviewer synchronously for this specific section
    from mether.services.research.writer import WriterAgent
    from mether.services.research.reviewer import ReviewerAgent
    
    writer = WriterAgent(orch.db, orch.llm, orch.bus)
    reviewer = ReviewerAgent(orch.db, orch.llm, orch.bus)
    
    refreshed_sec = await orch.get_section(section_id)
    draft = await writer.draft_section(task_id, refreshed_sec)
    await orch.update_section_content(section_id, "completed", content=draft)
    
    refreshed_sec = await orch.get_section(section_id)
    validated = await reviewer.verify_and_polish(task_id, refreshed_sec)
    await orch.update_section_content(section_id, "completed", validated=validated)
    
    return {"success": True, "validated_content": validated}

@router.post("/research/{task_id}/delivery")
async def deliver_report(request: Request, task_id: str, body: DeliveryRequest) -> dict[str, Any]:
    orch = request.app.state.research_orchestrator
    task = await orch.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    from mether.services.research.exporter import ExportAgent
    exporter = ExportAgent(orch.db, orch.bus)
    
    # Compile
    file_path = await exporter.export_report(task_id, body.template, body.format)
    
    # Store export metadata in DB
    query = """
        INSERT INTO export_metadata (task_id, format, template_used, delivery_channel, destination, exported_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    await orch.db._run_query(
        query,
        task_id, body.format, body.template, body.delivery_channel, body.destination or file_path, time.time(),
        is_write=True
    )
    
    return {
        "success": True,
        "file_location": file_path,
        "format": body.format,
        "delivery_channel": body.delivery_channel
    }

# ------------------------------------------------------------------
# Chief of Staff Models & Routes

class GoalCreateRequest(BaseModel):
    title: str
    description: str
    category: str
    target_date: Optional[str] = None

class GoalUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_date: Optional[str] = None
    status: Optional[str] = None

class TaskCreateRequest(BaseModel):
    milestone_id: str
    goal_id: str
    title: str
    description: str
    priority: str
    due_date: str
    time_estimate_mins: int = 60

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    time_estimate_mins: Optional[int] = None
    time_invested_mins: Optional[int] = None

class SubtaskToggleRequest(BaseModel):
    status: str

@router.post("/cos/goals")
async def create_goal(request: Request, body: GoalCreateRequest) -> dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    goal_id = await orch.create_goal(body.title, body.description, body.category, body.target_date)
    return {"goal_id": goal_id, "status": "queued"}

@router.get("/cos/goals")
async def list_goals(request: Request) -> List[Dict[str, Any]]:
    orch = request.app.state.chief_of_staff_orchestrator
    return await orch.get_goals()

@router.get("/cos/goals/{goal_id}")
async def get_goal(request: Request, goal_id: str) -> Dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    goal = await orch.get_goal_detail(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@router.put("/cos/goals/{goal_id}")
async def update_goal(request: Request, goal_id: str, body: GoalUpdateRequest) -> dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    await orch.update_goal(goal_id, body.model_dump(exclude_unset=True))
    return {"success": True}

@router.delete("/cos/goals/{goal_id}")
async def delete_goal(request: Request, goal_id: str) -> dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    await orch.delete_goal(goal_id)
    return {"success": True}

@router.post("/cos/tasks")
async def create_task(request: Request, body: TaskCreateRequest) -> dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    task_id = await orch.create_task(
        body.milestone_id, body.goal_id, body.title, body.description, body.priority, body.due_date, body.time_estimate_mins
    )
    return {"task_id": task_id}

@router.put("/cos/tasks/{task_id}")
async def update_task(request: Request, task_id: str, body: TaskUpdateRequest) -> dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    await orch.update_task(task_id, body.model_dump(exclude_unset=True))
    return {"success": True}

@router.put("/cos/subtasks/{subtask_id}")
async def toggle_subtask(request: Request, subtask_id: str, body: SubtaskToggleRequest) -> dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    await orch.toggle_subtask(subtask_id, body.status)
    return {"success": True}

@router.get("/cos/daily")
async def get_daily_priorities(request: Request) -> Dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    return await orch.get_daily_priorities()

@router.post("/cos/daily/generate")
async def generate_daily_priorities(request: Request) -> Dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    return await orch.generate_daily_priorities()

@router.get("/cos/review/weekly")
async def get_weekly_review(request: Request) -> Dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    review = await orch.get_weekly_review()
    if not review:
        return {}
    return review

@router.post("/cos/review/generate")
async def generate_weekly_review(request: Request) -> Dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    return await orch.generate_weekly_review()

@router.get("/cos/dashboard")
async def get_dashboard(request: Request) -> Dict[str, Any]:
    orch = request.app.state.chief_of_staff_orchestrator
    goals = await orch.get_goals()
    daily = await orch.get_daily_priorities()
    review = await orch.get_weekly_review() or {}
    recommendations = await orch.get_recommendations()

    # Calculate active vs overdue tasks count
    all_active_tasks = await orch.db._run_query(
        "SELECT due_date, priority FROM tasks WHERE status != 'completed'"
    )
    overdue_count = 0
    today_date = time.strftime("%Y-%m-%d")
    for t in all_active_tasks:
        if t["due_date"] and not t["due_date"].startswith("+") and t["due_date"] < today_date:
            overdue_count += 1

    return {
        "goals": goals,
        "daily": daily,
        "review": review,
        "recommendations": recommendations,
        "stats": {
            "goals_count": len(goals),
            "pending_tasks_count": len(all_active_tasks),
            "overdue_tasks_count": overdue_count,
            "current_streak": max([g["streak"] for g in goals]) if goals else 0
        }
    }

