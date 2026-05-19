# Building Tools for METHER OS

Tools are the primary way to extend METHER OS capabilities.
Each tool gives the AI agent a new action it can take on your behalf.

## Quick Start

Create a file in `backend/src/mether/tools/`:

```python
from mether.tools.base import BaseTool, ToolResult, SecurityLevel

class MyTool(BaseTool):
    name = "my_tool"
    description = """
    Describe what this tool does clearly.
    List available actions and their parameters.
    The LLM reads this description to decide when to use this tool.
    """
    security_level = SecurityLevel.READ
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        if action == "get_data":
            result = await self._fetch_data(kwargs.get("query"))
            return ToolResult(success=True, data=result)
        
        return ToolResult(
            success=False,
            error=f"Unknown action: {action}"
        )
    
    async def _fetch_data(self, query: str) -> dict:
        # Your implementation here
        pass
```

Register in `backend/src/mether/main.py`:

```python
from mether.tools.my_tool import MyTool
registry.register(MyTool())
```

## Security Levels

| Level | Constant | Behavior |
|-------|----------|----------|
| 0 | SecurityLevel.READ | Executes immediately |
| 1 | SecurityLevel.WRITE | Executes immediately, logs |
| 2 | SecurityLevel.DANGEROUS | Requires user confirmation |

## Tool Registry

Tools self-register their schemas for LLM tool-calling.
The agent automatically learns about new tools on startup.

## Testing Your Tool

```python
# backend/tests/test_tools.py
@pytest.mark.asyncio
async def test_my_tool():
    tool = MyTool()
    result = await tool.execute(action="get_data", query="test")
    assert result.success
    assert "data" in result.data
```
