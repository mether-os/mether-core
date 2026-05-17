import pytest
from mether.tools.base import ToolResult, SecurityLevel

def test_tool_result_success():
    result = ToolResult(success=True, data={"key": "value"})
    assert result.success is True
    assert result.data["key"] == "value"
    assert result.error is None

def test_tool_result_failure():
    result = ToolResult(success=False, error="something failed")
    assert result.success is False
    assert result.error == "something failed"

def test_security_levels():
    assert SecurityLevel.READ < SecurityLevel.WRITE
    assert SecurityLevel.WRITE < SecurityLevel.DANGEROUS

@pytest.mark.asyncio
async def test_system_tool():
    from mether.tools.system import SystemTool
    tool = SystemTool()
    result = await tool.execute()
    assert result.success is True
    assert "cpu_percent" in result.data
    assert "ram_percent" in result.data
