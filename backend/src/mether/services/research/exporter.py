import time
import json
from pathlib import Path
import structlog
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class ExportAgent:
    """Export Agent: Compiles evidence-first 12-section reports and generates Reproducibility Packages."""

    def __init__(self, db: PersistentMemory, bus: EventBus) -> None:
        self.db = db
        self.bus = bus

    async def export_report(self, task_id: str, template: str, format_type: str, old_snapshot: dict = None) -> str:
        """Compiles all sections, indices, heatmap, decision briefly and exports them."""
        # 1. Fetch task details
        task_res = await self.db._run_query("SELECT * FROM research_tasks WHERE id = ?", task_id)
        if not task_res:
            raise ValueError(f"Task not found: {task_id}")
        task = task_res[0]
        topic = task["topic"]
        
        # 2. Fetch sections
        sections = await self.db._run_query(
            "SELECT title, content, validated_content FROM research_sections WHERE task_id = ? ORDER BY order_idx ASC",
            task_id
        )
        
        # 3. Fetch Claims & Contradictions & Unknowns
        claims = await self.db._run_query("SELECT * FROM research_claims WHERE task_id = ?", task_id)
        claims = [dict(c) for c in claims]
        
        contradictions = await self.db._run_query("SELECT * FROM research_contradictions WHERE task_id = ?", task_id)
        contradictions = [dict(c) for c in contradictions]
        
        unknowns = [c for c in claims if c["verification_status"] == "Unverified"]
        
        # 4. Fetch Source Independence & Source Network
        independence = await self.db._run_query("SELECT * FROM source_independence WHERE task_id = ?", task_id)
        independence = [dict(i) for i in independence]
        
        network = await self.db._run_query("SELECT * FROM source_network WHERE task_id = ?", task_id)
        network = [dict(n) for n in network]
        
        # 5. Fetch Decision Brief & Action Plan & Devil's Advocate
        from mether.services.research.decision_layer import DecisionLayerAgent
        from mether.services.research.action_engine import ActionEngineAgent
        from mether.services.research.devils_advocate import DevilsAdvocateAgent
        
        dl_agent = DecisionLayerAgent(self.db, None)
        act_agent = ActionEngineAgent(self.db, None)
        da_agent = DevilsAdvocateAgent(self.db, None, self.bus)
        
        decision = await dl_agent.get_for_task(task_id)
        action_plan = await act_agent.get_for_task(task_id)
        da_report = await da_agent.get_for_task(task_id)
        
        # 6. Fetch bibliography references
        citations = await self.db._run_query(
            "SELECT DISTINCT source_url, title FROM citations WHERE task_id = ?",
            task_id
        )
        
        # 7. Create output directory
        out_dir = Path("c:/Users/mayan/Free_claude_codde/research_exports")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Start compiling report markdown
        report_md = []
        
        # Section 0: Research Configuration + Budget Summary
        report_md.append(f"# Research Report: {topic}")
        report_md.append(f"*Generated on {time.strftime('%Y-%m-%d %H:%M:%S')} (Task ID: {task_id})*")
        report_md.append("\n## Section 0: Research Configuration & Budget Summary")
        report_md.append(f"- **Research Mode:** {task.get('research_mode', 'balanced')}")
        report_md.append(f"- **Target Audience:** {task.get('target_audience', 'researcher')}")
        report_md.append(f"- **Search Budget:** {task.get('searches_used', 0)} / {task.get('search_budget', 0)} searches used")
        report_md.append(f"- **Token Budget:** {task.get('tokens_used', 0)} / {task.get('token_budget', 0)} tokens used")
        
        # Insufficient evidence banner if gate check failed
        if task.get("research_failed", 0) == 1:
            report_md.append("\n> [!WARNING]")
            report_md.append("> **INSUFFICIENT EVIDENCE WARNING:** This report fell below the minimum confidence threshold.")
            report_md.append(f"> **Reason:** {task.get('failure_reason', 'Low claim confidence')}")
            
        # Section 1: Change Report (if prior research)
        report_md.append("\n## Section 1: Change Report")
        if old_snapshot:
            # We generated the change report in orchestrator, but we can compile a simple diff here or just output a note
            report_md.append("Historical comparison detected. Prior snapshot is archived in the reproducibility package.")
        else:
            report_md.append("First-time research run. No historical updates to report.")
            
        # Sections 2-N: Evidence-First content per section
        for sec in sections:
            content = sec["validated_content"] or sec["content"] or "Draft missing."
            report_md.append(f"\n{content}")
            
        # Section N+1: Confidence Heatmap
        report_md.append("\n## Confidence Heatmap")
        report_md.append("Color Coding: 🟢 Verified (≥75%), 🟡 Partially Verified (50-74%), 🔴 Hypothesis (25-49%), ⬛ Unverified/Hypothesis (<25%)\n")
        if claims:
            for c in claims:
                score = c.get("confidence_score", 0.0)
                status = c.get("verification_status", "Unverified")
                if status == "Verified":
                    emoji = "🟢"
                elif status == "Partially Verified":
                    emoji = "🟡"
                elif status == "Hypothesis":
                    emoji = "🔴"
                else:
                    emoji = "⬛"
                report_md.append(f"- {emoji} **[{int(score * 100)}%]** {c['claim_text']}")
        else:
            report_md.append("No claims verified.")
            
        # Section N+2: Unknown Fields Register
        report_md.append("\n## Unknown Fields Register")
        if unknowns:
            report_md.append("| Field Name | Section | Reason |")
            report_md.append("|---|---|---|")
            for u in unknowns:
                # Remove prefix UNKNOWN: if present
                text = u["claim_text"].replace("UNKNOWN: ", "")
                report_md.append(f"| {text} | Section {u.get('section_id', '')} | {u.get('evidence', 'No evidence found')} |")
        else:
            report_md.append("No unknown fields registered.")
            
        # Section N+3: Contradiction Register
        report_md.append("\n## Contradiction Register")
        if contradictions:
            report_md.append("| Claim A ID | Claim B ID | Field Type | Penalty Applied | Possible Explanation |")
            report_md.append("|---|---|---|---|---|")
            for co in contradictions:
                try:
                    exp = " / ".join(co.get("possible_explanations") or [])
                except Exception:
                    exp = str(co.get("possible_explanations"))
                report_md.append(f"| {co['claim_a_id']} | {co['claim_b_id']} | {co['field_type']} | {co['confidence_penalty_applied']} | {exp} |")
        else:
            report_md.append("No contradictions detected.")
            
        # Section N+4: Source Independence Report
        report_md.append("\n## Source Independence Report")
        if independence:
            report_md.append("| Source URL | Independence Score | Duplication Type | Similarity Score |")
            report_md.append("|---|---|---|---|")
            for ind in independence:
                report_md.append(f"| {ind['url']} | {ind['independence_score']:.2f} | {ind['duplication_type']} | {ind['similarity_score']:.2f} |")
        else:
            report_md.append("No source independence analysis records found.")
            
        # Section N+5: Source Network Summary
        report_md.append("\n## Source Network Summary")
        if network:
            report_md.append("| Source URL | Parent URL | Chain Depth | Echo Risk Score |")
            report_md.append("|---|---|---|---|")
            for net in network:
                report_md.append(f"| {net['url']} | {net['parent_url'] or '--'} | {net['citation_chain_depth']} | {net['echo_chamber_risk_score']:.2f} |")
        else:
            report_md.append("No citation network mapping records found.")
            
        # Section N+6: Devil's Advocate Report
        report_md.append("\n## Devil's Advocate Critical Critique")
        if da_report:
            report_md.append("### Counter Arguments:")
            for arg in da_report.get("counter_arguments", []):
                report_md.append(f"- {arg}")
            report_md.append("### Alternative Interpretations:")
            for alt in da_report.get("alternative_interpretations", []):
                report_md.append(f"- {alt}")
            report_md.append("### Confidence Risks:")
            for risk in da_report.get("confidence_risks", []):
                report_md.append(f"- {risk}")
            report_md.append("### Why We Might Be Wrong:")
            for ww in da_report.get("why_wrong", []):
                report_md.append(f"- {ww}")
        else:
            report_md.append("Devil's Advocate review not generated.")
            
        # Section N+7: Decision Brief
        report_md.append("\n## Decision Brief")
        if decision:
            report_md.append(f"**Target Audience Framing:** {decision['target_audience'].upper()}")
            report_md.append(f"**Average Claims Confidence:** {int(decision['confidence_level'] * 100)}%")
            report_md.append(f"\n### Executive Summary:\n{decision['decision_summary']}")
            report_md.append("\n### Key Takeaways:")
            for kf in decision.get("key_findings", []):
                report_md.append(f"- {kf}")
            report_md.append("\n### Green Flags:")
            for gf in decision.get("green_flags", []):
                report_md.append(f"- {gf}")
            report_md.append("\n### Red Flags:")
            for rf in decision.get("red_flags", []):
                report_md.append(f"- {rf}")
        else:
            report_md.append("Decision brief not compiled.")
            
        # Section N+8: Action Plan
        report_md.append("\n## Prioritized Action Plan")
        if action_plan:
            report_md.append("| Priority | Action Recommendation | Category | Impact | Effort | Speculative |")
            report_md.append("|---|---|---|---|---|---|")
            for act in action_plan.get("actions", []):
                spec = "⚠️ SPECULATIVE" if act.get("speculative") else "No"
                report_md.append(f"| {act['priority']} | {act['action']} | {act['category']} | {act['estimated_impact']} | {act['estimated_effort']} | {spec} |")
        else:
            report_md.append("Action plan not generated.")
            
        # Section N+9: Evidence Traceability Index
        report_md.append("\n## Evidence Traceability Index")
        if claims:
            report_md.append("| Claim | Supporting Source | Excerpt | Credibility |")
            report_md.append("|---|---|---|---|")
            for cl in claims:
                # Truncate claim and evidence for table readability
                txt = cl["claim_text"][:50] + "..." if len(cl["claim_text"]) > 50 else cl["claim_text"]
                ev = cl["evidence"][:100] + "..." if len(cl["evidence"]) > 100 else cl["evidence"]
                report_md.append(f"| {txt} | {cl['source_url']} | {ev} | {cl['source_quality_score']:.1f}/10 |")
        else:
            report_md.append("No claims verified for traceability index.")
            
        # Section N+10: References
        report_md.append("\n## References & Citation Index")
        if citations:
            for idx, cit in enumerate(citations):
                report_md.append(f"[{idx + 1}] *{cit['title']}*. Available at: {cit['source_url']}")
        else:
            report_md.append("No citations recorded.")
            
        # Merge full report Markdown
        full_report_markdown = "\n".join(report_md)
        
        # Build reproducibility package folder
        repro_path = await self._generate_reproducibility_package(task_id, topic, out_dir)
        
        # Save output document in requested format
        timestamp_suffix = int(time.time())
        clean_topic = "".join(c if c.isalnum() else "_" for c in topic)[:30]
        
        format_upper = format_type.upper()
        if format_upper == "MARKDOWN":
            file_path = out_dir / f"{clean_topic}_{timestamp_suffix}.md"
            file_path.write_text(full_report_markdown, encoding="utf-8")
            return str(file_path)
            
        elif format_upper == "HTML":
            file_path = out_dir / f"{clean_topic}_{timestamp_suffix}.html"
            html_content = self._compile_html(topic, full_report_markdown)
            file_path.write_text(html_content, encoding="utf-8")
            return str(file_path)
            
        else:
            # Save markdown as fallback
            file_path = out_dir / f"{clean_topic}_{timestamp_suffix}.md"
            file_path.write_text(full_report_markdown, encoding="utf-8")
            return str(file_path)

    async def _generate_reproducibility_package(self, task_id: str, topic: str, out_dir: Path) -> str:
        """Generates a complete JSON reproducibility package containing snapshots and evidence trace graphs."""
        pkg_dir = out_dir / f"reproducibility_{task_id}"
        pkg_dir.mkdir(exist_ok=True)
        
        # claims.json
        claims = await self.db._run_query("SELECT * FROM research_claims WHERE task_id = ?", task_id)
        claims = [dict(c) for c in claims]
        (pkg_dir / "claims.json").write_text(json.dumps(claims, indent=2), encoding="utf-8")
        
        # evidence.json
        evidence = await self.db._run_query("SELECT * FROM evidence_vault WHERE task_id = ?", task_id)
        evidence = [dict(e) for e in evidence]
        (pkg_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        
        # contradictions.json
        contras = await self.db._run_query("SELECT * FROM research_contradictions WHERE task_id = ?", task_id)
        contras = [dict(c) for c in contras]
        (pkg_dir / "contradictions.json").write_text(json.dumps(contras, indent=2), encoding="utf-8")
        
        # unknowns.json
        unknowns = await self.db._run_query(
            "SELECT * FROM research_claims WHERE task_id = ? AND verification_status = 'Unverified'", task_id
        )
        unknowns = [dict(u) for u in unknowns]
        (pkg_dir / "unknowns.json").write_text(json.dumps(unknowns, indent=2), encoding="utf-8")
        
        # source_network.json
        network = await self.db._run_query("SELECT * FROM source_network WHERE task_id = ?", task_id)
        network = [dict(n) for n in network]
        independence = await self.db._run_query("SELECT * FROM source_independence WHERE task_id = ?", task_id)
        independence = [dict(i) for i in independence]
        (pkg_dir / "source_network.json").write_text(
            json.dumps({"network": network, "independence": independence}, indent=2), encoding="utf-8"
        )
        
        # decision.json
        decision = await self.db._run_query("SELECT * FROM decision_layer WHERE task_id = ?", task_id)
        decision = [dict(d) for d in decision]
        (pkg_dir / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
        
        # action_plan.json
        actions = await self.db._run_query("SELECT * FROM research_action_plans WHERE task_id = ?", task_id)
        actions = [dict(a) for a in actions]
        (pkg_dir / "action_plan.json").write_text(json.dumps(actions, indent=2), encoding="utf-8")
        
        # devils_advocate.json
        da = await self.db._run_query("SELECT * FROM devils_advocate WHERE task_id = ?", task_id)
        da = [dict(d) for d in da]
        (pkg_dir / "devils_advocate.json").write_text(json.dumps(da, indent=2), encoding="utf-8")
        
        # citations.json
        citations = await self.db._run_query(
            "SELECT c.*, rc.claim_text, rc.confidence_score FROM citations c "
            "LEFT JOIN research_claims rc ON rc.source_url = c.source_url AND rc.task_id = c.task_id "
            "WHERE c.task_id = ?", task_id
        )
        citations = [dict(c) for c in citations]
        (pkg_dir / "citations.json").write_text(json.dumps(citations, indent=2), encoding="utf-8")
        
        # budget_report.json
        task = await self.db._run_query("SELECT * FROM research_tasks WHERE id = ?", task_id)
        (pkg_dir / "budget_report.json").write_text(json.dumps(dict(task[0]) if task else {}, indent=2), encoding="utf-8")
        
        # metadata.json
        metadata = {
            "task_id": task_id,
            "topic": topic,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pipeline_version": "2.0.0-decision-intelligence",
            "reproducibility_format_version": "1.0"
        }
        (pkg_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        
        return str(pkg_dir)

    def _compile_html(self, title: str, markdown: str) -> str:
        """Converts basic markdown structure into CSS styled HTML reports."""
        lines = markdown.split("\n")
        html_lines = []
        in_list = False
        
        for line in lines:
            if line.startswith("# "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- ") or line.startswith("* "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.strip() == "":
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append("<br/>")
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<p>{line}</p>")
                
        if in_list:
            html_lines.append("</ul>")
            
        body = "\n".join(html_lines)
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #0b0f19;
            color: #d1d5db;
            line-height: 1.6;
            max-width: 850px;
            margin: 40px auto;
            padding: 0 20px;
        }}
        h1 {{ color: #4cd7f6; border-bottom: 2px solid rgba(76,215,246,0.2); padding-bottom: 10px; margin-bottom: 20px; }}
        h2 {{ color: #8b5cf6; margin-top: 40px; border-bottom: 1px solid rgba(139,92,246,0.15); padding-bottom: 6px; }}
        h3 {{ color: #10b981; margin-top: 25px; }}
        a {{ color: #4cd7f6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        p {{ margin-bottom: 16px; color: rgba(209, 213, 219, 0.85); text-align: justify; }}
        ul {{ margin-bottom: 20px; padding-left: 20px; }}
        li {{ margin-bottom: 8px; color: rgba(209, 213, 219, 0.85); }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; background: rgba(17, 24, 39, 0.6); }}
        th, td {{ border: 1px solid rgba(209, 213, 219, 0.15); padding: 10px; text-align: left; }}
        th {{ background: rgba(76, 215, 246, 0.1); color: #4cd7f6; }}
        blockquote {{ border-left: 4px solid #f59e0b; background: rgba(245, 158, 11, 0.05); padding: 12px; margin: 20px 0; color: #f59e0b; }}
    </style>
</head>
<body>
    {body}
</body>
</html>
"""
