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
            # Create indexes for search performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_session ON observations(session_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_type ON observations(type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_res_sections ON research_sections(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_res_sources ON research_sources(task_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_res_citations ON citations(task_id);")

            # Ensure missing columns exist in research_tasks for existing installations
            for col in ["format_requested", "research_plan"]:
                try:
                    conn.execute(f"SELECT {col} FROM research_tasks LIMIT 1;")
                except sqlite3.OperationalError:
                    conn.execute(f"ALTER TABLE research_tasks ADD COLUMN {col} TEXT;")

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
