import time
import asyncio
from typing import Any, Dict
import structlog

logger = structlog.get_logger(__name__)

RESEARCH_MODES: Dict[str, Dict[str, Any]] = {
    "fast": {
        "searches_per_section": 5,
        "total_search_budget": 20,
        "time_budget": 60,
        "token_budget": 10_000,
        "confidence_threshold": 0.60,
        "min_report_threshold": 0.40,
    },
    "balanced": {
        "searches_per_section": 10,
        "total_search_budget": 50,
        "time_budget": 120,
        "token_budget": 25_000,
        "confidence_threshold": 0.75,
        "min_report_threshold": 0.50,
    },
    "thorough": {
        "searches_per_section": 20,
        "total_search_budget": 100,
        "time_budget": 300,
        "token_budget": 60_000,
        "confidence_threshold": 0.85,
        "min_report_threshold": 0.60,
    },
    "maximum": {
        "searches_per_section": 40,
        "total_search_budget": 200,
        "time_budget": 600,
        "token_budget": 120_000,
        "confidence_threshold": 0.95,
        "min_report_threshold": 0.70,
    },
}

class BudgetController:
    """Controls research budget: search count, time, and token usage."""

    def __init__(self, mode: str, db, task_id: str) -> None:
        self.mode = mode.lower() if mode.lower() in RESEARCH_MODES else "balanced"
        self.config = RESEARCH_MODES[self.mode]
        self.db = db
        self.task_id = task_id
        self.searches_used: int = 0
        self.tokens_used: int = 0
        self.time_started: float = time.time()
        self._lock = asyncio.Lock()

    @property
    def search_budget(self) -> int:
        return self.config["total_search_budget"]

    @property
    def time_budget(self) -> float:
        return self.config["time_budget"]

    @property
    def token_budget(self) -> int:
        return self.config["token_budget"]

    @property
    def confidence_threshold(self) -> float:
        return self.config["confidence_threshold"]

    @property
    def min_report_threshold(self) -> float:
        return self.config["min_report_threshold"]

    @property
    def searches_per_section(self) -> int:
        return self.config["searches_per_section"]

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.time_started

    def can_search(self) -> bool:
        if self.searches_used >= self.search_budget:
            logger.info("budget.search_exhausted", used=self.searches_used, budget=self.search_budget)
            return False
        if self.elapsed_seconds >= self.time_budget:
            logger.info("budget.time_exhausted", elapsed=self.elapsed_seconds, budget=self.time_budget)
            return False
        if self.tokens_used >= self.token_budget:
            logger.info("budget.token_exhausted", used=self.tokens_used, budget=self.token_budget)
            return False
        return True

    def can_use_tokens(self, estimate: int) -> bool:
        return (self.tokens_used + estimate) <= self.token_budget

    async def record_search(self) -> None:
        async with self._lock:
            self.searches_used += 1
        await self.db._run_query(
            "UPDATE research_tasks SET searches_used = ? WHERE id = ?",
            self.searches_used, self.task_id, is_write=True
        )

    async def record_tokens(self, count: int) -> None:
        async with self._lock:
            self.tokens_used += count
        await self.db._run_query(
            "UPDATE research_tasks SET tokens_used = ? WHERE id = ?",
            self.tokens_used, self.task_id, is_write=True
        )

    def is_budget_exhausted(self) -> bool:
        return (self.searches_used >= self.search_budget or
                self.elapsed_seconds >= self.time_budget or
                self.tokens_used >= self.token_budget)

    def is_below_failure_threshold(self, avg_confidence: float) -> bool:
        return avg_confidence < self.min_report_threshold

    def budget_status(self) -> dict:
        return {
            "mode": self.mode,
            "searches_used": self.searches_used,
            "search_budget": self.search_budget,
            "tokens_used": self.tokens_used,
            "token_budget": self.token_budget,
            "time_elapsed": round(self.elapsed_seconds, 1),
            "time_budget": self.time_budget,
            "confidence_threshold": self.confidence_threshold,
            "min_report_threshold": self.min_report_threshold,
        }
