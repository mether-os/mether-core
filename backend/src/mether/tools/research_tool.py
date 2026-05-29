from typing import Any
from mether.tools.base import BaseTool, ToolResult, SecurityLevel

class ResearchPipelineTool(BaseTool):
    name = "research_pipeline"
    description = """
    METHER OS Research, Synthesize, and Export Pipeline tool.
    Actions:
    - start: initiate a new research report task. params: topic, depth, length_target, scope, template, format
    - status: check the status of a task. params: task_id
    - pause: pause a running task. params: task_id
    - resume: resume a paused task. params: task_id
    - cancel: cancel a task. params: task_id
    """
    security_level = SecurityLevel.WRITE  # requires confirmation/alert

    def __init__(self, orchestrator: Any = None) -> None:
        self.orchestrator = orchestrator

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["start", "status", "pause", "resume", "cancel"]},
                "topic": {"type": "string", "description": "Topic to research"},
                "task_id": {"type": "string", "description": "ID of existing research task"},
                "depth": {"type": "string", "enum": ["quick", "deep", "comprehensive", "academic"], "default": "deep"},
                "length_target": {"type": "string", "enum": ["5_pages", "20_pages", "50_pages", "100_pages"], "default": "20_pages"},
                "scope": {"type": "string", "enum": ["web_only", "local_only", "web_local"], "default": "web_local"},
                "template": {"type": "string", "enum": ["research_report", "whitepaper", "academic_paper"], "default": "research_report"},
                "format": {"type": "string", "enum": ["PDF", "DOCX", "HTML", "Markdown", "PPTX"], "default": "Markdown"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, **kwargs) -> ToolResult:  # type: ignore[override]
        if not self.orchestrator:
            return ToolResult(success=False, error="Orchestrator not initialized.")
            
        try:
            if action == "start":
                topic = kwargs.get("topic")
                if not topic:
                    return ToolResult(success=False, error="Topic is required to start research.")
                    
                depth = kwargs.get("depth", "deep")
                length_target = kwargs.get("length_target", "20_pages")
                scope = kwargs.get("scope", "web_local")
                template = kwargs.get("template", "research_report")
                format_type = kwargs.get("format", "Markdown")
                
                # Setup default model routing
                routing = {
                    "planner": "nvidia_nim/z-ai/glm4.7",
                    "researcher": "nvidia_nim/z-ai/glm4.7",
                    "writer": "nvidia_nim/z-ai/glm4.7",
                    "reviewer": "nvidia_nim/z-ai/glm4.7"
                }
                
                task_id = await self.orchestrator.create_task(
                    topic, depth, length_target, scope, template, routing
                )
                # Set format_requested directly in DB
                await self.orchestrator.db._run_query(
                    "UPDATE research_tasks SET format_requested = ? WHERE id = ?",
                    format_type, task_id, is_write=True
                )
                
                await self.orchestrator.enqueue(task_id)
                return ToolResult(success=True, data={"task_id": task_id, "status": "queued"})
                
            elif action == "status":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required.")
                task_data = await self.orchestrator.get_task(task_id)
                if not task_data:
                    return ToolResult(success=False, error="Task not found.")
                return ToolResult(success=True, data=task_data)
                
            elif action == "pause":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required.")
                success = await self.orchestrator.pause(task_id)
                return ToolResult(success=success)
                
            elif action == "resume":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required.")
                await self.orchestrator.resume_task(task_id)
                return ToolResult(success=True)
                
            elif action == "cancel":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required.")
                success = await self.orchestrator.cancel(task_id)
                return ToolResult(success=success)
                
            else:
                return ToolResult(success=False, error="Unknown action")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
