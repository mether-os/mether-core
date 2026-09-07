import asyncio
import time
import uuid
import json
from typing import Any, Dict, List, Optional
import structlog
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient
from mether.services.chief_of_staff.planner_agent import PlannerAgent
from mether.services.chief_of_staff.execution_agent import ExecutionAgent
from mether.services.chief_of_staff.review_agent import ReviewAgent
from mether.services.chief_of_staff.recommendation_agent import RecommendationAgent

logger = structlog.get_logger(__name__)

class ChiefOfStaffOrchestrator:
    """Orchestrates Digital Chief of Staff goals, milestones, priorities, reviews, and metrics."""

    def __init__(self, persistent_memory: PersistentMemory, llm: LLMClient, bus: EventBus) -> None:
        self.db = persistent_memory
        self.llm = llm
        self.bus = bus
        self.planner = PlannerAgent(self.llm, self.bus)
        self.executor = ExecutionAgent(self.llm, self.bus)
        self.reviewer = ReviewAgent(self.llm, self.bus)
        self.recommender = RecommendationAgent(self.llm, self.bus)

    # ------------------------------------------------------------------
    # Goals CRUD & Plan Generation
    # ------------------------------------------------------------------

    async def create_goal(self, title: str, description: str, category: str, target_date: Optional[str] = None) -> str:
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"
        query = """
            INSERT INTO goals (
                id, title, description, category, target_date, status, health_score, streak, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db._run_query(
            query,
            goal_id, title, description, category, target_date, "pending", 100.0, 0, time.time(), time.time(),
            is_write=True
        )
        # Asynchronously trigger planner agent to decompose the goal
        asyncio.create_task(self.trigger_planner_agent(goal_id, title, description, category))
        return goal_id

    async def get_goals(self) -> List[Dict[str, Any]]:
        query = "SELECT * FROM goals ORDER BY created_at DESC"
        goals = await self.db._run_query(query)
        # Compute dynamic progress percentage for each goal
        result = []
        for g in goals:
            goal_id = g["id"]
            # Count total tasks
            tasks = await self.db._run_query("SELECT status FROM tasks WHERE goal_id = ?", goal_id)
            total = len(tasks)
            completed = sum(1 for t in tasks if t["status"] == "completed")
            progress = (completed / total * 100.0) if total > 0 else 0.0
            
            goal_dict = dict(g)
            goal_dict["progress"] = progress
            result.append(goal_dict)
        return result

    async def get_goal_detail(self, goal_id: str) -> Optional[Dict[str, Any]]:
        goals = await self.db._run_query("SELECT * FROM goals WHERE id = ?", goal_id)
        if not goals:
            return None
        goal = dict(goals[0])

        # Fetch milestones
        milestones = await self.db._run_query("SELECT * FROM milestones WHERE goal_id = ? ORDER BY order_idx ASC", goal_id)
        goal["milestones"] = []

        for m in milestones:
            m_dict = dict(m)
            # Fetch tasks for this milestone
            tasks = await self.db._run_query("SELECT * FROM tasks WHERE milestone_id = ? ORDER BY created_at ASC", m["id"])
            m_dict["tasks"] = []
            for t in tasks:
                t_dict = dict(t)
                # Fetch subtasks
                subtasks = await self.db._run_query("SELECT * FROM subtasks WHERE task_id = ? ORDER BY created_at ASC", t["id"])
                t_dict["subtasks"] = [dict(s) for s in subtasks]
                m_dict["tasks"].append(t_dict)
            goal["milestones"].append(m_dict)

        # Count total vs completed tasks
        all_tasks = await self.db._run_query("SELECT status FROM tasks WHERE goal_id = ?", goal_id)
        total = len(all_tasks)
        completed = sum(1 for t in all_tasks if t["status"] == "completed")
        goal["progress"] = (completed / total * 100.0) if total > 0 else 0.0

        return goal

    async def update_goal(self, goal_id: str, fields: Dict[str, Any]) -> None:
        if not fields:
            return
        sets = []
        params = []
        for k, v in fields.items():
            if k in ["title", "description", "category", "target_date", "status", "health_score", "streak"]:
                sets.append(f"{k} = ?")
                params.append(v)
        sets.append("updated_at = ?")
        params.append(time.time())
        params.append(goal_id)

        query = f"UPDATE goals SET {', '.join(sets)} WHERE id = ?"
        await self.db._run_query(query, *params, is_write=True)

    async def delete_goal(self, goal_id: str) -> None:
        # Cascade deletes are active, but SQLite needs explicit run for tables
        await self.db._run_query("DELETE FROM goals WHERE id = ?", goal_id, is_write=True)

    async def trigger_planner_agent(self, goal_id: str, title: str, description: str, category: str) -> None:
        """Asynchronously triggers Planner Agent, decomposes objective, and populates milestones/tasks in DB."""
        await self.bus.emit("ws.send", {
            "type": "cos_progress",
            "message": f"Planning milestones for goal: '{title}'...",
            "progress": 25.0
        })

        # Calculate offset target in days
        days_target = 60
        plan = await self.planner.generate_plan(title, description, category, days_target)

        # Insert milestones, tasks, and subtasks
        for m_idx, m in enumerate(plan):
            m_id = f"milestone_{uuid.uuid4().hex[:12]}"
            await self.db._run_query(
                "INSERT INTO milestones (id, goal_id, title, description, due_date, status, order_idx, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                m_id, goal_id, m["title"], m.get("description", ""), f"+{m.get('days_offset', 15)}d", "pending", m_idx + 1, time.time(),
                is_write=True
            )

            for t in m.get("tasks", []):
                t_id = f"task_{uuid.uuid4().hex[:12]}"
                await self.db._run_query(
                    "INSERT INTO tasks (id, milestone_id, goal_id, title, description, priority, status, due_date, time_estimate_mins, time_invested_mins, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    t_id, m_id, goal_id, t["title"], t.get("description", ""), t.get("priority", "medium"), "pending", f"+{m.get('days_offset', 15)}d", t.get("time_estimate_mins", 60), 0, time.time(), time.time(),
                    is_write=True
                )

                for st_title in t.get("subtasks", []):
                    st_id = f"subtask_{uuid.uuid4().hex[:12]}"
                    await self.db._run_query(
                        "INSERT INTO subtasks (id, task_id, title, status, created_at) VALUES (?, ?, ?, ?, ?)",
                        st_id, t_id, st_title, "pending", time.time(),
                        is_write=True
                    )

        # Set goal status to active
        await self.update_goal(goal_id, {"status": "in_progress"})
        await self.update_goal_health_score(goal_id)

        await self.bus.emit("ws.send", {
            "type": "cos_progress",
            "message": "Goal planning and task ingestion complete.",
            "progress": 100.0
        })
        # Emit a global updates sync trigger
        await self.bus.emit("ws.send", {"type": "cos_update"})

    # ------------------------------------------------------------------
    # Tasks & Subtasks Control
    # ------------------------------------------------------------------

    async def create_task(self, milestone_id: str, goal_id: str, title: str, description: str, priority: str, due_date: str, time_estimate_mins: int = 60) -> str:
        t_id = f"task_{uuid.uuid4().hex[:12]}"
        query = """
            INSERT INTO tasks (
                id, milestone_id, goal_id, title, description, priority, status, due_date, time_estimate_mins, time_invested_mins, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db._run_query(
            query,
            t_id, milestone_id, goal_id, title, description, priority, "pending", due_date, time_estimate_mins, 0, time.time(), time.time(),
            is_write=True
        )
        await self.update_goal_health_score(goal_id)
        await self.bus.emit("ws.send", {"type": "cos_update"})
        return t_id

    async def update_task(self, task_id: str, fields: Dict[str, Any]) -> None:
        if not fields:
            return
        sets = []
        params = []
        for k, v in fields.items():
            if k in ["title", "description", "priority", "status", "due_date", "time_estimate_mins", "time_invested_mins"]:
                sets.append(f"{k} = ?")
                params.append(v)
        sets.append("updated_at = ?")
        params.append(time.time())
        params.append(task_id)

        query = f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?"
        await self.db._run_query(query, *params, is_write=True)

        # Log progress if status changes
        if "status" in fields:
            tasks = await self.db._run_query("SELECT goal_id, title FROM tasks WHERE id = ?", task_id)
            if tasks:
                goal_id = tasks[0]["goal_id"]
                title = tasks[0]["title"]
                status = fields["status"]
                await self.log_progress(goal_id, task_id, "status_change", f"Task '{title}' status changed to {status}")
                await self.update_goal_health_score(goal_id)

        await self.bus.emit("ws.send", {"type": "cos_update"})

    async def toggle_subtask(self, subtask_id: str, status: str) -> None:
        query = "UPDATE subtasks SET status = ? WHERE id = ?"
        await self.db._run_query(query, status, subtask_id, is_write=True)
        # Find goal_id
        res = await self.db._run_query(
            "SELECT t.goal_id FROM subtasks s JOIN tasks t ON s.task_id = t.id WHERE s.id = ?",
            subtask_id
        )
        if res:
            await self.update_goal_health_score(res[0]["goal_id"])
        await self.bus.emit("ws.send", {"type": "cos_update"})

    # ------------------------------------------------------------------
    # Progress Logging & Streaks
    # ------------------------------------------------------------------

    async def log_progress(self, goal_id: str, task_id: Optional[str], log_type: str, notes: str) -> None:
        query = "INSERT INTO progress_logs (goal_id, task_id, log_type, notes, timestamp) VALUES (?, ?, ?, ?, ?)"
        await self.db._run_query(query, goal_id, task_id, log_type, notes, time.time(), is_write=True)

    async def update_goal_health_score(self, goal_id: str) -> None:
        """Calculate dynamic consistency stats, streaks, and health score."""
        # 1. Fetch all tasks
        tasks = await self.db._run_query("SELECT id, status, priority, due_date FROM tasks WHERE goal_id = ?", goal_id)
        if not tasks:
            return

        total_count = len(tasks)
        completed_count = sum(1 for t in tasks if t["status"] == "completed")

        # Linear completion percent
        completion_ratio = completed_count / total_count if total_count > 0 else 1.0
        health = completion_ratio * 100.0

        # 2. Overdue penalties (subtract 10% per overdue high task)
        now_str = time.strftime("%Y-%m-%d")
        overdue_penalty = 0.0
        for t in tasks:
            if t["status"] != "completed" and t["due_date"]:
                # If due date format is YYYY-MM-DD and past
                if not t["due_date"].startswith("+") and t["due_date"] < now_str:
                    penalty = 15.0 if t["priority"] == "high" else (10.0 if t["priority"] == "medium" else 5.0)
                    overdue_penalty += penalty

        health -= overdue_penalty

        # 3. Streaks: count consecutive days with logged completed status progress in progress_logs
        logs = await self.db._run_query(
            "SELECT timestamp FROM progress_logs WHERE goal_id = ? AND log_type = 'status_change' AND notes LIKE '%completed%' ORDER BY timestamp DESC",
            goal_id
        )
        
        streak = 0
        if logs:
            # Simple day-by-day streak analysis
            unique_days = sorted(list(set([time.strftime("%Y-%m-%d", time.localtime(log_item["timestamp"])) for log_item in logs])), reverse=True)
            
            yesterday_sec = time.time() - 86400
            today_day = time.strftime("%Y-%m-%d")
            yesterday_day = time.strftime("%Y-%m-%d", time.localtime(yesterday_sec))

            # Streak continues if last log was today or yesterday
            if unique_days[0] in [today_day, yesterday_day]:
                streak = 1
                for idx in range(len(unique_days) - 1):
                    day_curr = unique_days[idx]
                    day_next = unique_days[idx + 1]
                    # Parse days
                    t_curr = time.mktime(time.strptime(day_curr, "%Y-%m-%d"))
                    t_next = time.mktime(time.strptime(day_next, "%Y-%m-%d"))
                    if abs(t_curr - t_next) <= 90000: # approx 1 day with tolerance
                        streak += 1
                    else:
                        break

        # Streak health bonus
        if streak >= 5:
            health += 10.0

        health = max(0.0, min(100.0, health))

        # Save health and streak
        await self.update_goal(goal_id, {"health_score": health, "streak": streak})

    # ------------------------------------------------------------------
    # Daily priorities caching & Generation
    # ------------------------------------------------------------------

    async def get_daily_priorities(self) -> Dict[str, Any]:
        today_date = time.strftime("%Y-%m-%d")
        res = await self.db._run_query("SELECT * FROM daily_priorities WHERE date = ?", today_date)
        if res:
            row = res[0]
            return {
                "date": row["date"],
                "priorities": json.loads(row["priorities_json"]),
                "blockers": json.loads(row["blockers_json"]),
                "focus_area": row["focus_area"]
            }

        # Otherwise trigger ExecutionAgent automatically
        return await self.generate_daily_priorities()

    async def generate_daily_priorities(self) -> Dict[str, Any]:
        today_date = time.strftime("%Y-%m-%d")
        
        # Gather pending tasks
        active_tasks = await self.db._run_query(
            "SELECT t.id, t.title, t.priority, t.due_date, g.title as goal_title FROM tasks t JOIN goals g ON t.goal_id = g.id WHERE t.status != 'completed'"
        )
        
        # Gather overdue tasks
        overdue_tasks = []
        for t in active_tasks:
            if t["due_date"] and not t["due_date"].startswith("+") and t["due_date"] < today_date:
                overdue_tasks.append(t)

        # Get recent vitals
        import psutil
        vitals_dict = {"cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent}

        # Context details
        recent_summaries = await self.db.get_recent_summaries(3)
        context_notes = f"System resources: {vitals_dict}\n"
        if recent_summaries:
            context_notes += "Recent memories:\n" + "\n".join([f"- {s['summary']}" for s in recent_summaries])

        # Run ExecutionAgent
        result = await self.executor.generate_daily_priorities(active_tasks, overdue_tasks, context_notes, today_date)

        # Insert or replace
        await self.db._run_query("DELETE FROM daily_priorities WHERE date = ?", today_date, is_write=True)
        await self.db._run_query(
            "INSERT INTO daily_priorities (date, priorities_json, blockers_json, focus_area, generated_at) VALUES (?, ?, ?, ?, ?)",
            today_date, json.dumps(result.get("priorities", [])), json.dumps(result.get("blockers", [])), result.get("focus_area", "General Execution"), time.time(),
            is_write=True
        )

        return {
            "date": today_date,
            "priorities": result.get("priorities", []),
            "blockers": result.get("blockers", []),
            "focus_area": result.get("focus_area", "General Execution")
        }

    # ------------------------------------------------------------------
    # Weekly Review Generation
    # ------------------------------------------------------------------

    async def get_weekly_review(self) -> Optional[Dict[str, Any]]:
        reviews = await self.db._run_query("SELECT * FROM weekly_reviews ORDER BY generated_at DESC LIMIT 1")
        return dict(reviews[0]) if reviews else None

    async def generate_weekly_review(self) -> Dict[str, str]:
        # Last 7 days
        seven_days_ago = time.time() - (7 * 86400)
        week_start = time.strftime("%Y-%m-%d", time.localtime(seven_days_ago))
        week_end = time.strftime("%Y-%m-%d")

        # Fetch completed tasks in the last 7 days
        completed_tasks = await self.db._run_query(
            "SELECT t.*, g.title as goal_title FROM tasks t JOIN goals g ON t.goal_id = g.id WHERE t.status = 'completed' AND t.updated_at >= ?",
            seven_days_ago
        )

        # Fetch overdue tasks
        missed_tasks = await self.db._run_query(
            "SELECT t.*, g.title as goal_title FROM tasks t JOIN goals g ON t.goal_id = g.id WHERE t.status != 'completed'"
        )
        overdue_tasks = [t for t in missed_tasks if t["due_date"] and not t["due_date"].startswith("+") and t["due_date"] < week_end]

        # Fetch progress logs
        logs = await self.db._run_query(
            "SELECT notes FROM progress_logs WHERE timestamp >= ? ORDER BY timestamp DESC",
            seven_days_ago
        )
        progress_notes = [log_item["notes"] for log_item in logs if log_item["notes"]]

        # Run ReviewAgent
        result = await self.reviewer.generate_weekly_review(completed_tasks, overdue_tasks, progress_notes, week_start, week_end)

        review_id = f"review_{uuid.uuid4().hex[:12]}"
        await self.db._run_query(
            "INSERT INTO weekly_reviews (id, week_start, week_end, accomplishments, missed_targets, risks, recommendations, generated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            review_id, week_start, week_end, result["accomplishments"], result["missed_targets"], result["risks"], result["recommendations"], time.time(),
            is_write=True
        )

        return result

    # ------------------------------------------------------------------
    # Dynamic Context Recommendations
    # ------------------------------------------------------------------

    async def get_recommendations(self) -> str:
        # Retrieve goals
        goals = await self.get_goals()

        # Mock events & chats as calendars and observation logs
        recent_obs = await self.db._run_query(
            "SELECT content FROM observations WHERE type = 'user_message' ORDER BY timestamp DESC LIMIT 5"
        )
        chats = [o["content"] for o in recent_obs]

        # Hardware vitals
        import psutil
        vitals = {"cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent, "uptime": int(time.time() - psutil.boot_time())}

        # Fetch upcoming events
        upcoming_events = []
        try:
            # We can mock this simply if no calendar events
            pass
        except Exception:
            pass

        return await self.recommender.generate_recommendations(goals, upcoming_events, chats, vitals)
