"""Persistent database-backed memory system for METHER OS.

Preserves context across sessions by recording tool usage observations,
generating semantic summaries using the LLM, and allowing structured searches.
"""

from __future__ import annotations

import sqlite3
import time
import asyncio
from pathlib import Path
from typing import Any
import structlog

from mether.agent.llm import LLMClient
from mether.events.bus import EventBus

logger = structlog.get_logger(__name__)


class PersistentMemory:
    """Manages SQLite storage for observations and semantic summaries."""

    def __init__(self, db_path: Path | str, llm: LLMClient, bus: EventBus) -> None:
        self.db_path = db_path
        if not (isinstance(db_path, str) and db_path.startswith(":")):
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.llm = llm
        self.bus = bus
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database tables and indexes."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    start_time REAL,
                    end_time REAL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp REAL,
                    type TEXT,
                    content TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    summary TEXT,
                    keywords TEXT
                );
            """)
            # Research Tasks
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_tasks (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    depth TEXT NOT NULL,
                    length_target TEXT NOT NULL,
                    knowledge_scope TEXT NOT NULL,
                    export_template TEXT NOT NULL,
                    model_routing TEXT NOT NULL,
                    progress_percent REAL DEFAULT 0.0,
                    estimated_completion_time REAL,
                    output_path TEXT,
                    error_message TEXT,
                    format_requested TEXT,
                    research_plan TEXT
                );
            """)
            # Research Sections
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    order_idx INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    instructions TEXT,
                    content TEXT,
                    validated_content TEXT,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
                );
            """)
            # Research Sources
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    snippet TEXT,
                    source_type TEXT NOT NULL,
                    publication_date TEXT,
                    author TEXT,
                    domain TEXT,
                    credibility_score REAL NOT NULL,
                    trust_score REAL NOT NULL,
                    extracted_facts TEXT,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
                );
            """)
            # Citations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS citations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    title TEXT,
                    quote TEXT NOT NULL,
                    citation_text TEXT NOT NULL,
                    section_reference TEXT,
                    page_reference TEXT,
                    retrieval_timestamp REAL NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
                );
            """)
            # Local Knowledge
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    ingested_at REAL NOT NULL,
                    extracted_text_snippet TEXT,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
                );
            """)
            # Export Metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS export_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    template_used TEXT NOT NULL,
                    delivery_channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    exported_at REAL NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
                );
            """)

            # Chief of Staff Tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    target_date TEXT,
                    status TEXT NOT NULL,
                    health_score REAL DEFAULT 100.0,
                    streak INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS milestones (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    status TEXT NOT NULL,
                    order_idx INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    milestone_id TEXT NOT NULL,
                    goal_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    due_date TEXT,
                    time_estimate_mins INTEGER DEFAULT 0,
                    time_invested_mins INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY(milestone_id) REFERENCES milestones(id) ON DELETE CASCADE,
                    FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subtasks (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS progress_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id TEXT NOT NULL,
                    task_id TEXT,
                    log_type TEXT NOT NULL,
                    notes TEXT,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weekly_reviews (
                    id TEXT PRIMARY KEY,
                    week_start TEXT NOT NULL,
                    week_end TEXT NOT NULL,
                    accomplishments TEXT NOT NULL,
                    missed_targets TEXT NOT NULL,
                    risks TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    generated_at REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_priorities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    priorities_json TEXT NOT NULL,
                    blockers_json TEXT NOT NULL,
                    focus_area TEXT NOT NULL,
                    generated_at REAL NOT NULL
                );
            """)

            # Create indexes for search performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_session ON observations(session_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_type ON observations(type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_res_sections ON research_sections(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_res_sources ON research_sources(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_res_citations ON citations(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cos_milestones ON milestones(goal_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cos_tasks_goal ON tasks(goal_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cos_tasks_milestone ON tasks(milestone_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cos_subtasks ON subtasks(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cos_progress_logs ON progress_logs(goal_id);")

            # Decision Intelligence Engine Tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence_vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    snapshot_text TEXT,
                    retrieved_at REAL NOT NULL,
                    quality_score REAL NOT NULL,
                    independence_score REAL,
                    extracted_claims_json TEXT,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    section_id INTEGER,
                    claim_text TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    source_id INTEGER,
                    source_url TEXT NOT NULL,
                    vault_id INTEGER,
                    verification_status TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    confidence_source_quality REAL NOT NULL,
                    confidence_cross_validation REAL NOT NULL,
                    confidence_recency REAL NOT NULL,
                    confidence_independence REAL NOT NULL,
                    contradiction_penalty REAL DEFAULT 0.0,
                    cross_validation_count INTEGER DEFAULT 0,
                    recency_score REAL NOT NULL,
                    source_quality_score REAL NOT NULL,
                    retrieved_timestamp REAL NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_contradictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    claim_a_id INTEGER,
                    claim_b_id INTEGER,
                    source_a_url TEXT,
                    source_b_url TEXT,
                    field_type TEXT NOT NULL,
                    possible_explanations TEXT NOT NULL,
                    human_review_recommended INTEGER NOT NULL DEFAULT 1,
                    confidence REAL NOT NULL,
                    confidence_penalty_applied REAL NOT NULL DEFAULT 0.20,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_independence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    independence_score REAL NOT NULL,
                    duplicate_of_url TEXT,
                    duplication_type TEXT,
                    similarity_score REAL,
                    flagged_at REAL NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_network (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    parent_url TEXT,
                    claim_count INTEGER DEFAULT 0,
                    echo_chamber_risk_score REAL DEFAULT 0.0,
                    citation_chain_depth INTEGER DEFAULT 0,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_layer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    key_findings TEXT NOT NULL,
                    green_flags TEXT NOT NULL,
                    red_flags TEXT NOT NULL,
                    open_questions TEXT NOT NULL,
                    risks TEXT NOT NULL,
                    opportunities TEXT NOT NULL,
                    decision_summary TEXT NOT NULL,
                    confidence_level REAL NOT NULL,
                    target_audience TEXT NOT NULL,
                    devils_advocate_summary TEXT,
                    research_failure INTEGER DEFAULT 0,
                    failure_reason TEXT,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_action_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    actions_json TEXT NOT NULL,
                    next_steps_json TEXT NOT NULL,
                    quick_wins_json TEXT NOT NULL,
                    long_term_actions_json TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS devils_advocate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    counter_arguments_json TEXT NOT NULL,
                    alternative_interpretations_json TEXT NOT NULL,
                    confidence_risks_json TEXT NOT NULL,
                    why_wrong_json TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_hash TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    recommendation_text TEXT NOT NULL,
                    confidence_at_time REAL NOT NULL,
                    predicted_outcome TEXT,
                    actual_outcome TEXT,
                    user_feedback TEXT,
                    outcome_timestamp REAL,
                    correct INTEGER,
                    topic_hash TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS accuracy_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_date TEXT NOT NULL,
                    total_predictions INTEGER NOT NULL,
                    correct_predictions INTEGER NOT NULL,
                    prediction_accuracy REAL NOT NULL,
                    verification_success_rate REAL NOT NULL,
                    contradiction_detection_rate REAL NOT NULL,
                    confidence_calibration_score REAL NOT NULL,
                    avg_source_independence_score REAL NOT NULL,
                    computed_at REAL NOT NULL
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS human_review_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    claim_id INTEGER,
                    source_url TEXT NOT NULL,
                    snapshot_excerpt TEXT NOT NULL,
                    review_reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reviewer_notes TEXT,
                    reviewed_at REAL,
                    FOREIGN KEY(task_id) REFERENCES research_tasks(id)
                );
            """)

            # Add indexes for Decision Intelligence Engine
            conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_vault ON evidence_vault(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_claims ON research_claims(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contradictions ON research_contradictions(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source_independence ON source_independence(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_history ON research_history(topic_hash);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_outcomes ON recommendation_outcomes(task_id);")

            # Ensure missing columns exist in research_tasks for existing installations
            for col in ["format_requested", "research_plan"]:
                try:
                    conn.execute(f"SELECT {col} FROM research_tasks LIMIT 1;")
                except sqlite3.OperationalError:
                    conn.execute(f"ALTER TABLE research_tasks ADD COLUMN {col} TEXT;")

            # New column migrations on research_tasks for Decision Intelligence Engine
            for col_def in [
                ("research_mode", "TEXT DEFAULT 'balanced'"),
                ("search_budget", "INTEGER DEFAULT 10"),
                ("time_budget_seconds", "INTEGER DEFAULT 120"),
                ("token_budget", "INTEGER DEFAULT 25000"),
                ("searches_used", "INTEGER DEFAULT 0"),
                ("tokens_used", "INTEGER DEFAULT 0"),
                ("time_started", "REAL"),
                ("target_audience", "TEXT DEFAULT 'researcher'"),
                ("human_review_enabled", "INTEGER DEFAULT 0"),
                ("research_failed", "INTEGER DEFAULT 0"),
                ("failure_reason", "TEXT"),
                ("failure_confidence", "REAL"),
                ("avg_confidence", "REAL"),
            ]:
                col_name, col_type = col_def
                try:
                    conn.execute(f"SELECT {col_name} FROM research_tasks LIMIT 1;")
                except sqlite3.OperationalError:
                    conn.execute(f"ALTER TABLE research_tasks ADD COLUMN {col_name} {col_type};")

            # Ensure missing columns exist in research_sources for existing installations
            try:
                conn.execute("SELECT extracted_facts FROM research_sources LIMIT 1;")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE research_sources ADD COLUMN extracted_facts TEXT;")

            conn.commit()
        logger.info("memory.db_initialized", path=str(self.db_path))

    async def _run_query(self, query: str, *args: Any, is_write: bool = False) -> Any:
        """Run a database query in a separate thread to keep the event loop non-blocking."""
        def _execute():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, args)
                if is_write:
                    conn.commit()
                    return cursor.lastrowid
                return [dict(row) for row in cursor.fetchall()]
        return await asyncio.get_running_loop().run_in_executor(None, _execute)

    # ------------------------------------------------------------------
    # Session & Observation Logging
    # ------------------------------------------------------------------

    async def start_session(self, session_id: str) -> None:
        """Log the start of a session."""
        query = "INSERT OR IGNORE INTO sessions (id, start_time) VALUES (?, ?)"
        await self._run_query(query, session_id, time.time(), is_write=True)

    async def add_observation(self, session_id: str, obs_type: str, content: str) -> int:
        """Insert a tool call, tool result, prompt, or response observation."""
        query = "INSERT INTO observations (session_id, timestamp, type, content) VALUES (?, ?, ?, ?)"
        db_id = await self._run_query(query, session_id, time.time(), obs_type, content, is_write=True)
        return db_id

    # ------------------------------------------------------------------
    # Search and Memory Retrieval (3-Layer Workflow Pattern)
    # ------------------------------------------------------------------

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memory summaries and observations using text matching.

        Returns a list of compact results with their IDs.
        """
        # Search summaries
        summary_query = """
            SELECT id, timestamp, 'summary' as type, summary as content, keywords
            FROM summaries
            WHERE summary LIKE ? OR keywords LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        like_pattern = f"%{query}%"
        summary_results = await self._run_query(summary_query, like_pattern, like_pattern, limit)

        # Search observations
        obs_query = """
            SELECT id, timestamp, type, content, session_id
            FROM observations
            WHERE type IN ('user_message', 'agent_response') AND content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        obs_results = await self._run_query(obs_query, like_pattern, limit)

        combined = []
        for r in summary_results:
            combined.append({
                "id": f"summary-{r['id']}",
                "db_id": r['id'],
                "type": "summary",
                "timestamp": r['timestamp'],
                "content": r['content'],
                "keywords": r['keywords']
            })
        for r in obs_results:
            combined.append({
                "id": f"obs-{r['id']}",
                "db_id": r['id'],
                "type": r['type'],
                "timestamp": r['timestamp'],
                "content": r['content'],
                "session_id": r.get('session_id')
            })

        combined.sort(key=lambda x: x["timestamp"], reverse=True)
        return combined[:limit]

    async def get_timeline(self, observation_id: int, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve chronological context (preceding/succeeding observations) around an observation."""
        res = await self._run_query("SELECT session_id FROM observations WHERE id = ?", observation_id)
        if not res:
            return []
        session_id = res[0]["session_id"]

        query = """
            SELECT id, timestamp, type, content, session_id
            FROM observations
            WHERE session_id = ? AND id >= ? - ? AND id <= ? + ?
            ORDER BY id ASC
        """
        return await self._run_query(query, session_id, observation_id, limit, observation_id, limit)

    async def get_observations(self, ids: list[int]) -> list[dict[str, Any]]:
        """Retrieve full details of specific observations by ID."""
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        query = f"""
            SELECT id, timestamp, type, content, session_id
            FROM observations
            WHERE id IN ({placeholders})
            ORDER BY id ASC
        """
        def _execute():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, ids)
                return [dict(row) for row in cursor.fetchall()]
        return await asyncio.get_running_loop().run_in_executor(None, _execute)

    async def get_recent_summaries(self, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve the most recent summaries to inject into the system prompt."""
        query = "SELECT summary, keywords FROM summaries ORDER BY timestamp DESC LIMIT ?"
        return await self._run_query(query, limit)

    # ------------------------------------------------------------------
    # Background Semantic Compression
    # ------------------------------------------------------------------

    async def summarize_interaction(self, session_id: str) -> None:
        """Asynchronously summarize the latest interaction and save it as a memory."""
        try:
            # Fetch last 20 observations for the session to find the last user turn
            obs = await self._run_query(
                "SELECT id, type, content FROM observations WHERE session_id = ? ORDER BY id DESC LIMIT 20",
                session_id
            )
            if not obs:
                return

            obs = list(reversed(obs))

            # Find the start of the latest interaction (user_message)
            user_idx = -1
            for i, o in enumerate(obs):
                if o["type"] == "user_message":
                    user_idx = i

            if user_idx == -1:
                return

            current_interaction = obs[user_idx:]

            # Format current interaction for LLM summarization
            lines = []
            for o in current_interaction:
                t = o["type"]
                c = o["content"]
                if t == "user_message":
                    lines.append(f"User: {c}")
                elif t == "tool_call":
                    lines.append(f"Agent calls tool: {c}")
                elif t == "tool_result":
                    lines.append(f"Tool returns: {c}")
                elif t == "agent_response":
                    lines.append(f"Agent response: {c}")

            transcript = "\n".join(lines)

            prompt = (
                "You are an agentic memory compressor.\n"
                "Summarize the following interaction between the user and METHER agent.\n"
                "Explain what the user wanted, what tools were called and what they returned, and what the final outcome was.\n"
                "Keep the summary extremely concise (1-2 sentences, max 50 words).\n"
                "Also extract 3-5 space-separated keywords/tags (e.g. 'whatsapp calendar process chrome email') describing this interaction.\n\n"
                "Example response format:\n"
                "Summary: User wanted to check if Chrome was open. Agent ran process listing; Chrome was not running.\n"
                "Keywords: process chrome status listing\n\n"
                f"Interaction Transcript:\n{transcript}"
            )

            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a helpful memory compressor."
            )
            content_blocks = llm_resp.get("content", [])
            reply_text = content_blocks[0].get("text", "") if content_blocks else ""

            summary = ""
            keywords = ""
            for line in reply_text.splitlines():
                if line.lower().startswith("summary:"):
                    summary = line[len("summary:"):].strip()
                elif line.lower().startswith("keywords:"):
                    keywords = line[len("keywords:"):].strip()

            if not summary and reply_text:
                summary = reply_text.split("\n")[0].strip()

            if summary:
                await self._run_query(
                    "INSERT INTO summaries (timestamp, summary, keywords) VALUES (?, ?, ?)",
                    time.time(), summary, keywords, is_write=True
                )
                logger.info("memory.summary_saved", summary=summary[:100])
                await self.bus.emit("ws.send", {
                    "type": "log",
                    "module": "MEMORY",
                    "message": f"Saved Memory: {summary[:70]}..."
                })
        except Exception as e:
            logger.exception("memory.summarization_failed", error=str(e))
