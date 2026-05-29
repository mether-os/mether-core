import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock

from mether.memory.persistent_memory import PersistentMemory
from mether.tools.memory import SearchMemoryTool, MemoryTimelineTool, GetMemoryObservationsTool
from mether.events.bus import EventBus
from mether.tools.base import SecurityLevel


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(path)
    yield db_path
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass


@pytest.fixture
def mock_llm():
    client = AsyncMock()
    # Mock summarization response
    client.chat = AsyncMock(return_value={
        "content": [{
            "text": "Summary: User asked for something. Agent did it.\nKeywords: test execute tools"
        }]
    })
    return client


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.mark.asyncio
async def test_persistent_memory_lifecycle(temp_db_path, mock_llm, event_bus):
    memory = PersistentMemory(db_path=temp_db_path, llm=mock_llm, bus=event_bus)
    
    # Verify tables are initialized
    assert temp_db_path.exists()
    
    session_id = "test-session-123"
    await memory.start_session(session_id)
    
    # Add observations
    obs1 = await memory.add_observation(session_id, "user_message", "Hello METHER")
    obs2 = await memory.add_observation(session_id, "tool_call", "some_tool")
    obs3 = await memory.add_observation(session_id, "tool_result", "success")
    obs4 = await memory.add_observation(session_id, "agent_response", "Hi there")
    
    assert obs1 > 0
    assert obs2 > obs1
    
    # Retrieve timeline
    timeline = await memory.get_timeline(obs2, limit=2)
    assert len(timeline) > 0
    types = [t["type"] for t in timeline]
    assert "tool_call" in types
    assert "user_message" in types
    
    # Retrieve specific observations
    details = await memory.get_observations([obs1, obs4])
    assert len(details) == 2
    assert details[0]["content"] == "Hello METHER"
    assert details[1]["content"] == "Hi there"
    
    # Perform Search (check search behavior)
    search_results = await memory.search("METHER")
    assert len(search_results) > 0
    assert any("Hello METHER" in s["content"] for s in search_results)


@pytest.mark.asyncio
async def test_background_summarization(temp_db_path, mock_llm, event_bus):
    memory = PersistentMemory(db_path=temp_db_path, llm=mock_llm, bus=event_bus)
    session_id = "summary-session"
    
    await memory.start_session(session_id)
    await memory.add_observation(session_id, "user_message", "Make me a sandwich")
    await memory.add_observation(session_id, "tool_call", '{"name": "sandwich_maker"}')
    await memory.add_observation(session_id, "tool_result", '{"status": "completed"}')
    await memory.add_observation(session_id, "agent_response", "Here is your sandwich")
    
    # Trigger summarization
    await memory.summarize_interaction(session_id)
    
    # Verify LLM was called
    mock_llm.chat.assert_called_once()
    
    # Verify summary is stored
    recent = await memory.get_recent_summaries(limit=1)
    assert len(recent) == 1
    assert "User asked for something" in recent[0]["summary"]
    assert "test" in recent[0]["keywords"]


@pytest.mark.asyncio
async def test_memory_tools(temp_db_path, mock_llm, event_bus):
    memory = PersistentMemory(db_path=temp_db_path, llm=mock_llm, bus=event_bus)
    session_id = "tools-session"
    
    await memory.start_session(session_id)
    obs_id = await memory.add_observation(session_id, "user_message", "Search for code files")
    
    # Add dummy summary
    await memory._run_query(
        "INSERT INTO summaries (timestamp, summary, keywords) VALUES (?, ?, ?)",
        123.45, "Summarized code search activity", "code search file", is_write=True
    )
    
    # 1. Search tool
    search_tool = SearchMemoryTool(memory)
    assert search_tool.name == "search_memory"
    assert search_tool.security_level == SecurityLevel.READ
    
    res1 = await search_tool.execute("code")
    assert res1.success
    assert len(res1.data) > 0
    assert any(item["content"] == "Summarized code search activity" for item in res1.data)
    
    # 2. Timeline tool
    timeline_tool = MemoryTimelineTool(memory)
    res2 = await timeline_tool.execute(obs_id)
    assert res2.success
    assert len(res2.data) > 0
    
    # 3. Get observations tool
    get_obs_tool = GetMemoryObservationsTool(memory)
    res3 = await get_obs_tool.execute([obs_id])
    assert res3.success
    assert len(res3.data) == 1
    assert res3.data[0]["content"] == "Search for code files"
