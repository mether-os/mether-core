import asyncio
import time
import uuid
import json
from typing import Any, Dict, List, Optional
import structlog
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient

logger = structlog.get_logger(__name__)

class ResearchOrchestrator:
    """Orchestrates long-running multi-agent research task queues and lifecycle."""

    def __init__(self, persistent_memory: PersistentMemory, llm: LLMClient, bus: EventBus) -> None:
        self.db = persistent_memory
        self.llm = llm
        self.bus = bus
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.queue: List[str] = []
        self.semaphore = asyncio.Semaphore(2)  # Max 2 concurrent research jobs

    # ------------------------------------------------------------------
    # DB Access Layer
    # ------------------------------------------------------------------

    async def create_task(self, topic: str, depth: str, length_target: str, scope: str, template: str, routing: Dict[str, str]) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        query = """
            INSERT INTO research_tasks (
                id, topic, status, stage, created_at, updated_at,
                depth, length_target, knowledge_scope, export_template, model_routing, progress_percent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db._run_query(
            query,
            task_id, topic, "queued", "planning", time.time(), time.time(),
            depth, length_target, scope, template, json.dumps(routing), 0.0,
            is_write=True
        )
        return task_id

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        res = await self.db._run_query("SELECT * FROM research_tasks WHERE id = ?", task_id)
        return dict(res[0]) if res else None

    async def update_task_status(self, task_id: str, status: str, stage: str = None) -> None:
        if stage:
            query = "UPDATE research_tasks SET status = ?, stage = ?, updated_at = ? WHERE id = ?"
            await self.db._run_query(query, status, stage, time.time(), task_id, is_write=True)
        else:
            query = "UPDATE research_tasks SET status = ?, updated_at = ? WHERE id = ?"
            await self.db._run_query(query, status, time.time(), task_id, is_write=True)

    async def update_task_progress(self, task_id: str, progress: float, eta: float = None) -> None:
        if eta is not None:
            query = "UPDATE research_tasks SET progress_percent = ?, estimated_completion_time = ?, updated_at = ? WHERE id = ?"
            await self.db._run_query(query, progress, eta, time.time(), task_id, is_write=True)
        else:
            query = "UPDATE research_tasks SET progress_percent = ?, updated_at = ? WHERE id = ?"
            await self.db._run_query(query, progress, time.time(), task_id, is_write=True)

    async def save_research_plan(self, task_id: str, plan_json: str) -> None:
        query = "UPDATE research_tasks SET research_plan = ?, updated_at = ? WHERE id = ?"
        await self.db._run_query(query, plan_json, time.time(), task_id, is_write=True)

    async def add_section(self, task_id: str, title: str, order_idx: int, instructions: str) -> int:
        query = """
            INSERT INTO research_sections (task_id, title, order_idx, status, instructions)
            VALUES (?, ?, ?, ?, ?)
        """
        return await self.db._run_query(query, task_id, title, order_idx, "pending", instructions, is_write=True)

    async def get_sections(self, task_id: str) -> List[Dict[str, Any]]:
        query = "SELECT * FROM research_sections WHERE task_id = ? ORDER BY order_idx ASC"
        return await self.db._run_query(query, task_id)

    async def get_section(self, section_id: int) -> Optional[Dict[str, Any]]:
        res = await self.db._run_query("SELECT * FROM research_sections WHERE id = ?", section_id)
        return dict(res[0]) if res else None

    async def update_section_content(self, section_id: int, status: str, content: str = None, validated: str = None) -> None:
        if content is not None and validated is not None:
            query = "UPDATE research_sections SET status = ?, content = ?, validated_content = ? WHERE id = ?"
            await self.db._run_query(query, status, content, validated, section_id, is_write=True)
        elif content is not None:
            query = "UPDATE research_sections SET status = ?, content = ? WHERE id = ?"
            await self.db._run_query(query, status, content, section_id, is_write=True)
        elif validated is not None:
            query = "UPDATE research_sections SET status = ?, validated_content = ? WHERE id = ?"
            await self.db._run_query(query, status, validated, section_id, is_write=True)
        else:
            query = "UPDATE research_sections SET status = ? WHERE id = ?"
            await self.db._run_query(query, status, section_id, is_write=True)

    # ------------------------------------------------------------------
    # Queue Management
    # ------------------------------------------------------------------

    async def enqueue(self, task_id: str) -> None:
        self.queue.append(task_id)
        await self.update_task_status(task_id, "queued")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "planning",
            "status": "queued",
            "message": "Research task enqueued.",
            "progress": 0.0
        })
        asyncio.create_task(self._process_queue())

    async def pause(self, task_id: str) -> bool:
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            self.running_tasks.pop(task_id, None)
            await self.update_task_status(task_id, "paused")
            await self.bus.emit("ws.send", {
                "type": "research_progress",
                "task_id": task_id,
                "stage": "paused",
                "status": "paused",
                "message": "Research task paused.",
                "progress": 0.0
            })
            return True
        return False

    async def cancel(self, task_id: str) -> bool:
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            self.running_tasks.pop(task_id, None)
        if task_id in self.queue:
            self.queue.remove(task_id)
        await self.update_task_status(task_id, "cancelled")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "cancelled",
            "status": "cancelled",
            "message": "Research task cancelled.",
            "progress": 0.0
        })
        return True

    async def _process_queue(self) -> None:
        if not self.queue:
            return

        async with self.semaphore:
            if not self.queue:
                return
            task_id = self.queue.pop(0)
            
            task = asyncio.create_task(self._run_task_pipeline(task_id))
            self.running_tasks[task_id] = task
            try:
                await task
            except asyncio.CancelledError:
                logger.info("research.task_cancelled_or_paused", task_id=task_id)
            except Exception as e:
                logger.exception("research.task_failed", task_id=task_id, error=str(e))
                await self.update_task_status(task_id, "failed")
                await self.db._run_query("UPDATE research_tasks SET error_message = ? WHERE id = ?", str(e), task_id, is_write=True)
                await self.bus.emit("ws.send", {
                    "type": "research_progress",
                    "task_id": task_id,
                    "stage": "failed",
                    "status": "failed",
                    "message": f"Task failed: {str(e)}",
                    "progress": 0.0
                })
            finally:
                self.running_tasks.pop(task_id, None)

    # ------------------------------------------------------------------
    # Pipeline Orchestration Logic
    # ------------------------------------------------------------------

    async def _run_task_pipeline(self, task_id: str) -> None:
        logger.info("research.pipeline_start", task_id=task_id)
        await self.update_task_status(task_id, "running", "planning")
        
        task_data = await self.get_task(task_id)
        if not task_data:
            return
            
        topic = task_data["topic"]
        
        # 1. Planner Agent: Plan decomposition
        from mether.services.research.researcher import PlannerAgent
        planner = PlannerAgent(self.llm, self.bus)
        
        # In case we resume from past outline
        sections = await self.get_sections(task_id)
        if not sections:
            await self.bus.emit("ws.send", {
                "type": "research_progress",
                "task_id": task_id,
                "stage": "planning",
                "status": "running",
                "message": "Generating research report outline...",
                "progress": 5.0
            })
            outline = await planner.generate_outline(topic, task_data["depth"], task_data["length_target"])
            
            # Save sections
            for idx, item in enumerate(outline):
                await self.add_section(task_id, item["title"], idx + 1, item.get("instructions", ""))
            
            await self.save_research_plan(task_id, json.dumps(outline))
            sections = await self.get_sections(task_id)
            
        # Check human approval requirement
        # Simple policy: if depth is academic or comprehensive, wait for outline approval
        # We can simulate/check if task stage is already outline approved or if outline approval is needed
        if task_data["stage"] == "planning" and task_data["depth"] in ["academic", "comprehensive"]:
            await self.update_task_status(task_id, "paused", "awaiting_outline_approval")
            await self.bus.emit("ws.send", {
                "type": "research_progress",
                "task_id": task_id,
                "stage": "awaiting_outline_approval",
                "status": "paused",
                "message": "Outline generated. Awaiting human approval.",
                "progress": 15.0,
                "details": {"outline": sections}
            })
            return

        # 2. Gather information (Research Agent)
        await self.update_task_status(task_id, "running", "collecting")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "collecting",
            "status": "running",
            "message": "Gathering facts and evaluating credibility...",
            "progress": 20.0
        })
        
        from mether.services.research.researcher import ResearchAgent
        researcher = ResearchAgent(self.db, self.llm, self.bus)
        await researcher.gather_information(task_id, topic, sections)
        
        # 3. Writer Agent: Draft Sections
        await self.update_task_status(task_id, "running", "writing")
        from mether.services.research.writer import WriterAgent
        writer = WriterAgent(self.db, self.llm, self.bus)
        
        total_sections = len(sections)
        for idx, sec in enumerate(sections):
            if sec["status"] == "completed":
                continue
            
            progress = 20.0 + (idx / total_sections) * 50.0
            await self.update_task_progress(task_id, progress)
            await self.bus.emit("ws.send", {
                "type": "research_progress",
                "task_id": task_id,
                "stage": "writing",
                "status": "running",
                "message": f"Drafting section {idx+1}/{total_sections}: {sec['title']}",
                "progress": progress
            })
            
            draft_content = await writer.draft_section(task_id, sec)
            await self.update_section_content(sec["id"], "completed", content=draft_content)
            
        # Awaiting Draft Approval
        if task_data["depth"] in ["academic", "comprehensive"]:
            await self.update_task_status(task_id, "paused", "awaiting_draft_approval")
            refreshed_sections = await self.get_sections(task_id)
            await self.bus.emit("ws.send", {
                "type": "research_progress",
                "task_id": task_id,
                "stage": "awaiting_draft_approval",
                "status": "paused",
                "message": "Draft report compiled. Awaiting section approvals.",
                "progress": 70.0,
                "details": {"sections": refreshed_sections}
            })
            return

        # 4. Reviewer Agent: Consistency & Fact Checks
        await self.update_task_status(task_id, "running", "reviewing")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "reviewing",
            "status": "running",
            "message": "Cross-verifying findings and resolving citations...",
            "progress": 75.0
        })
        
        from mether.services.research.reviewer import ReviewerAgent
        reviewer = ReviewerAgent(self.db, self.llm, self.bus)
        refreshed_sections = await self.get_sections(task_id)
        
        for idx, sec in enumerate(refreshed_sections):
            validated_content = await reviewer.verify_and_polish(task_id, sec)
            await self.update_section_content(sec["id"], "completed", validated=validated_content)

        # 5. Export Agent
        await self.update_task_status(task_id, "running", "exporting")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "exporting",
            "status": "running",
            "message": "Generating final report in requested formats...",
            "progress": 90.0
        })
        
        from mether.services.research.exporter import ExportAgent
        exporter = ExportAgent(self.db, self.bus)
        final_path = await exporter.export_report(task_id, task_data["export_template"], task_data["format_requested"] or "Markdown")
        
        # Complete
        await self.db._run_query("UPDATE research_tasks SET status = ?, stage = ?, progress_percent = 100.0, output_path = ?, updated_at = ? WHERE id = ?", "completed", "completed", final_path, time.time(), task_id, is_write=True)
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "completed",
            "status": "completed",
            "message": "Research report generated and saved locally.",
            "progress": 100.0,
            "details": {
                "file_location": final_path,
                "sources_count": len(await self.db._run_query("SELECT id FROM research_sources WHERE task_id = ?", task_id))
            }
        })
        logger.info("research.pipeline_complete", task_id=task_id, path=final_path)
