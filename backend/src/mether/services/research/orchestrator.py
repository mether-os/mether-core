import asyncio
import time
import uuid
import json
import hashlib
from typing import Any, Dict, List, Optional
import structlog
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient
from mether.services.research.budget_controller import BudgetController
from mether.services.research.evidence_vault import EvidenceVault

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

    async def create_task(
        self,
        topic: str,
        depth: str,
        length_target: str,
        scope: str,
        template: str,
        routing: Dict[str, str],
        research_mode: str = "balanced",
        target_audience: str = "researcher",
        human_review_enabled: int = 0
    ) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        query = """
            INSERT INTO research_tasks (
                id, topic, status, stage, created_at, updated_at,
                depth, length_target, knowledge_scope, export_template, model_routing, progress_percent,
                research_mode, target_audience, human_review_enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db._run_query(
            query,
            task_id, topic, "queued", "planning", time.time(), time.time(),
            depth, length_target, scope, template, json.dumps(routing), 0.0,
            research_mode, target_audience, human_review_enabled,
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

    async def resume_task(self, task_id: str) -> bool:
        """Resumes a paused task by enqueuing it again."""
        task_data = await self.get_task(task_id)
        if task_data and task_data["status"] == "paused":
            await self.enqueue(task_id)
            return True
        return False

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
    # Pipeline Orchestration Logic (11-Stage Decision Engine)
    # ------------------------------------------------------------------

    async def _run_task_pipeline(self, task_id: str) -> None:
        logger.info("research.pipeline_start", task_id=task_id)
        
        task_data = await self.get_task(task_id)
        if not task_data:
            return
            
        topic = task_data["topic"]
        mode = task_data.get("research_mode", "balanced")
        audience = task_data.get("target_audience", "researcher")
        
        # Initialize Core Budget and Vault
        budget = BudgetController(mode=mode, db=self.db, task_id=task_id)
        evidence_vault = EvidenceVault(db=self.db)
        
        # STAGE 1: planning
        await self.update_task_status(task_id, "running", "planning")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "planning",
            "status": "running",
            "message": "Initializing 11-stage Decision Intelligence Pipeline...",
            "progress": 5.0,
            "budget": budget.budget_status()
        })
        
        topic_hash = self._get_topic_hash(topic)
        old_snapshot = await self._check_research_history(topic_hash)
        
        # Planner outline generation
        from mether.services.research.researcher import PlannerAgent
        planner = PlannerAgent(self.llm, self.bus)
        
        sections = await self.get_sections(task_id)
        if not sections:
            outline = await planner.generate_outline(topic, task_data["depth"], task_data["length_target"])
            for idx, item in enumerate(outline):
                await self.add_section(task_id, item["title"], idx + 1, item.get("instructions", ""))
            await self.save_research_plan(task_id, json.dumps(outline))
            sections = await self.get_sections(task_id)
            
        # STAGE 2: collecting
        await self.update_task_status(task_id, "running", "collecting")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "collecting",
            "status": "running",
            "message": f"Collecting factual claims under {mode.upper()} budget constraints...",
            "progress": 20.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.researcher import ResearchAgent
        researcher = ResearchAgent(self.db, self.llm, self.bus, budget, evidence_vault)
        collect_results = await researcher.gather_information(task_id, topic, sections)
        
        claims = collect_results["claims"]
        unknowns = collect_results["unknowns"]
        sources = collect_results["sources"]
        
        # STAGE 3: vaulting (Done inline with collection, emit status)
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "vaulting",
            "status": "running",
            "message": "Archiving all raw sources inside Evidence Vault...",
            "progress": 35.0,
            "budget": budget.budget_status()
        })
        await asyncio.sleep(0.5)
        
        # STAGE 4: verifying
        await self.update_task_status(task_id, "running", "verifying")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "verifying",
            "status": "running",
            "message": "Verifying claims, scanning skepticism vulnerabilities...",
            "progress": 40.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.skeptic import SkepticAgent
        from mether.services.research.fact_checker import FactCheckerAgent
        skeptic = SkepticAgent(self.db)
        fact_checker = FactCheckerAgent(self.db, self.llm, self.bus, budget, evidence_vault)
        
        challenges = await skeptic.challenge_claims(task_id, claims)
        # Verify high-severity challenges
        await fact_checker.fact_check_claims(task_id, challenges, researcher._search_duckduckgo)
        
        # Refresh claims from db after verification updates
        claims = await self.db._run_query("SELECT * FROM research_claims WHERE task_id = ?", task_id)
        claims = [dict(c) for c in claims]
        
        # STAGE 5: contradicting
        await self.update_task_status(task_id, "running", "contradicting")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "contradicting",
            "status": "running",
            "message": "Detecting database numerical and semantic contradictions...",
            "progress": 50.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.contradiction_engine import ContradictionEngine
        contra_engine = ContradictionEngine(self.db, self.llm)
        contradictions = await contra_engine.detect_contradictions(task_id, claims)
        
        # STAGE 6: networking
        await self.update_task_status(task_id, "running", "networking")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "networking",
            "status": "running",
            "message": "Mapping citation loops and analyzing source independence...",
            "progress": 60.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.source_independence import SourceIndependenceAnalyzer
        from mether.services.research.source_network import SourceNetworkMapper
        indep_analyzer = SourceIndependenceAnalyzer(self.db)
        net_mapper = SourceNetworkMapper(self.db)
        
        independence_recs = await indep_analyzer.analyze_independence(task_id, sources)
        network_summary = await net_mapper.build_network(task_id, sources, independence_recs)
        
        # STAGE 7: gate_check
        await self.update_task_status(task_id, "running", "gate_check")
        avg_conf = sum(c["confidence_score"] for c in claims) / len(claims) if claims else 0.0
        failed_gate = await self._check_failure_gate(task_id, avg_conf, budget)
        
        # Human evidence review gate
        if bool(task_data.get("human_review_enabled", 0)):
            from mether.services.research.human_review import HumanReviewGate
            hr_gate = HumanReviewGate(self.db)
            
            # Queue weak/hypothesis claims for review
            weak_claims = [c for c in claims if c["verification_status"] in ("Hypothesis", "Unverified")]
            for wc in weak_claims[:3]:
                await hr_gate.queue_for_review(
                    task_id=task_id,
                    claim_id=wc["id"],
                    source_url=wc["source_url"],
                    snapshot_excerpt=wc["evidence"],
                    review_reason="Weak validation or hypothesis claim"
                )
                
            if not await hr_gate.is_review_complete(task_id):
                # Suspend pipeline, pause task
                await self.update_task_status(task_id, "paused", "human_review")
                await self.bus.emit("ws.send", {
                    "type": "research_progress",
                    "task_id": task_id,
                    "stage": "human_review",
                    "status": "paused",
                    "message": "Pipeline suspended. Awaiting human verification reviews.",
                    "progress": 65.0,
                    "budget": budget.budget_status()
                })
                return  # Pipeline execution suspends here
                
        # STAGE 8: writing
        await self.update_task_status(task_id, "running", "writing")
        from mether.services.research.writer import WriterAgent
        writer = WriterAgent(self.db, self.llm, self.bus)
        
        total_sections = len(sections)
        for idx, sec in enumerate(sections):
            progress = 65.0 + (idx / total_sections) * 15.0
            await self.update_task_progress(task_id, progress)
            await self.bus.emit("ws.send", {
                "type": "research_progress",
                "task_id": task_id,
                "stage": "writing",
                "status": "running",
                "message": f"Drafting evidence-first section {idx+1}/{total_sections}: {sec['title']}",
                "progress": progress,
                "budget": budget.budget_status()
            })
            
            # Filter arguments specifically for this section
            sec_claims = [c for c in claims if c.get("section_id") == sec["id"]]
            v_claims = [c for c in sec_claims if c["verification_status"] in ("Verified", "Partially Verified")]
            u_claims = [c for c in sec_claims if c["verification_status"] in ("Hypothesis", "Unverified")]
            sec_unknowns = [u for u in unknowns if u.get("section_id") == sec["id"]]
            sec_challenges = [ch for ch in challenges if ch.get("claim_id") in [c["id"] for c in sec_claims]]
            
            draft_content = await writer.draft_section(
                task_id=task_id,
                section=sec,
                verified_claims=v_claims,
                unverified_claims=u_claims,
                unknowns=sec_unknowns,
                skeptic_challenges=sec_challenges
            )
            await self.update_section_content(sec["id"], "completed", content=draft_content)
            
        # STAGE 9: advocating
        await self.update_task_status(task_id, "running", "advocating")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "advocating",
            "status": "running",
            "message": "Invoking Devil's Advocate Agent for vulnerability audit...",
            "progress": 80.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.devils_advocate import DevilsAdvocateAgent
        da_agent = DevilsAdvocateAgent(self.db, self.llm, self.bus)
        refreshed_sections = await self.get_sections(task_id)
        
        # Generate preliminary decision brief parameters for critical review
        prelim_decision = {
            "avg_confidence": avg_conf,
            "claims_count": len(claims),
            "unknowns_count": len(unknowns)
        }
        da_report = await da_agent.challenge_report(task_id, refreshed_sections, prelim_decision)
        
        # STAGE 10: deciding
        await self.update_task_status(task_id, "running", "deciding")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "deciding",
            "status": "running",
            "message": f"Synthesizing audience-tailored ({audience.upper()}) decision layer...",
            "progress": 85.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.decision_layer import DecisionLayerAgent
        dl_agent = DecisionLayerAgent(self.db, self.llm)
        decision_brief = await dl_agent.generate_decision(
            task_id=task_id,
            topic=topic,
            sections_content=refreshed_sections,
            claims_summary=claims,
            contradictions=contradictions,
            unknowns=unknowns,
            da_report=da_report,
            target_audience=audience,
            avg_confidence=avg_conf,
            research_failed=failed_gate,
            failure_reason=f"Confidence too low for mode {mode} threshold" if failed_gate else None
        )
        
        # STAGE 11: acting
        await self.update_task_status(task_id, "running", "acting")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "acting",
            "status": "running",
            "message": "Generating Priority-Ranked Action Plans & Outcomes...",
            "progress": 90.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.action_engine import ActionEngineAgent
        from mether.services.research.outcome_tracker import OutcomeTrackerAgent
        act_agent = ActionEngineAgent(self.db, self.llm)
        tracker_agent = OutcomeTrackerAgent(self.db)
        
        v_claims = [c for c in claims if c["verification_status"] in ("Verified", "Partially Verified")]
        u_claims = [c for c in claims if c["verification_status"] in ("Hypothesis", "Unverified")]
        
        action_plan = await act_agent.generate_action_plan(
            task_id=task_id,
            topic=topic,
            decision_brief=decision_brief,
            verified_claims=v_claims,
            unverified_claims=u_claims,
            target_audience=audience
        )
        await tracker_agent.store_predictions(task_id, topic, action_plan, decision_brief)
        
        # STAGE 12: exporting
        await self.update_task_status(task_id, "running", "exporting")
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "exporting",
            "status": "running",
            "message": "Exporting structured report and Reproducibility Package...",
            "progress": 95.0,
            "budget": budget.budget_status()
        })
        
        from mether.services.research.exporter import ExportAgent
        exporter = ExportAgent(self.db, self.bus)
        final_path = await exporter.export_report(
            task_id,
            task_data["export_template"],
            task_data["format_requested"] or "Markdown",
            old_snapshot=old_snapshot
        )
        
        # Save snapshot to research_history
        snapshot = {
            "claims": claims,
            "unknowns": unknowns,
            "contradictions": contradictions,
            "decision": decision_brief,
            "action_plan": action_plan
        }
        await self._store_research_history(task_id, topic_hash, snapshot)
        
        # Pipeline Complete
        await self.db._run_query(
            "UPDATE research_tasks SET status = ?, stage = ?, progress_percent = 100.0, output_path = ?, avg_confidence = ?, updated_at = ? WHERE id = ?",
            "completed", "completed", final_path, avg_conf, time.time(), task_id,
            is_write=True
        )
        
        await self.bus.emit("ws.send", {
            "type": "research_progress",
            "task_id": task_id,
            "stage": "completed",
            "status": "completed",
            "message": "Decision intelligence compilation successful.",
            "progress": 100.0,
            "details": {
                "file_location": final_path,
                "claims_verified": len(v_claims),
                "claims_unverified": len(u_claims),
                "contradictions": len(contradictions)
            }
        })
        logger.info("research.pipeline_complete", task_id=task_id, path=final_path)

    async def _check_failure_gate(self, task_id: str, avg_confidence: float, budget: BudgetController) -> bool:
        """Returns True and stores failure status if confidence falls below threshold."""
        if budget.is_below_failure_threshold(avg_confidence):
            reason = f"Average confidence {avg_confidence:.0%} below minimum threshold {budget.min_report_threshold:.0%} for {budget.mode} mode"
            await self.db._run_query(
                "UPDATE research_tasks SET research_failed=1, failure_reason=?, failure_confidence=? WHERE id=?",
                reason, avg_confidence, task_id, is_write=True
            )
            await self.bus.emit("ws.send", {
                "type": "research_progress",
                "task_id": task_id,
                "stage": "gate_check",
                "status": "warning",
                "message": f"⚠ RESEARCH FAILED: {reason}. Report will be generated with INSUFFICIENT EVIDENCE banner.",
                "progress": 65.0,
                "research_failed": True,
                "failure_reason": reason,
            })
            return True  # failed
        return False  # passed

    def _get_topic_hash(self, topic: str) -> str:
        """Returns normalized topic hash."""
        return hashlib.md5(topic.lower().strip().encode("utf-8")).hexdigest()[:12]

    async def _check_research_history(self, topic_hash: str) -> Optional[Dict]:
        """Queries historical research snapshots."""
        query = "SELECT snapshot_json FROM research_history WHERE topic_hash = ? ORDER BY id DESC LIMIT 1"
        res = await self.db._run_query(query, topic_hash)
        if res:
            try:
                return json.loads(res[0]["snapshot_json"])
            except Exception:
                return None
        return None

    async def _store_research_history(self, task_id: str, topic_hash: str, snapshot: Dict) -> None:
        """Stores a snapshot of the research in the history table."""
        query = """
            INSERT INTO research_history (topic_hash, task_id, snapshot_json, created_at)
            VALUES (?, ?, ?, ?)
        """
        await self.db._run_query(query, topic_hash, task_id, json.dumps(snapshot), time.time(), is_write=True)

    async def _generate_change_report(self, old_snapshot: Dict, new_claims: List[Dict]) -> str:
        """Generates a markdown change report explaining updates between runs."""
        old_claims = old_snapshot.get("claims", [])
        
        prompt = f"""You are a change analyst.
Compare the previous claims from a prior research task and the new claims from the current research task.
Explain what has changed, what new information was verified, and what was updated.

Previous Claims:
{json.dumps(old_claims, indent=2)}

New Claims:
{json.dumps(new_claims, indent=2)}

Provide a clean Markdown change report detailing updates, additions, and deletions.
No preambles, just output raw Markdown."""

        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a change report analyst."
            )
            content = resp.get("content", [])
            return content[0].get("text", "") if content else "No changes detected."
        except Exception as e:
            logger.warning("orchestrator.change_report_failed", error=str(e))
            return "Unable to generate change report."
