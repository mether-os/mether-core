"""System Control Tools for METHER OS."""

from typing import Any
import os
import glob
import subprocess
import platform
import time
from pathlib import Path

import psutil
import pyperclip
import mss
import asyncio

from mether.tools.base import BaseTool, ToolResult, SecurityLevel

class AppLaunchTool(BaseTool):
    name = "app_launch"
    description = "Open an application by name or path. Examples: 'open chrome', 'open vscode', 'open spotify', 'open notepad'"
    security_level = SecurityLevel.WRITE

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "The name or path of the app to launch"}
            },
            "required": ["app"]
        }

    async def execute(self, app: str, **kwargs) -> ToolResult:  # type: ignore[override]
        APP_ALIASES = {
            "chrome":    {"win": "chrome",          "linux": "google-chrome"},
            "firefox":   {"win": "firefox",         "linux": "firefox"},
            "vscode":    {"win": "code",            "linux": "code"},
            "terminal":  {"win": "wt",              "linux": "x-terminal-emulator"},
            "explorer":  {"win": "explorer",        "linux": "nautilus"},
            "notepad":   {"win": "notepad",         "linux": "gedit"},
            "spotify":   {"win": "spotify",         "linux": "spotify"},
            "discord":   {"win": "discord",         "linux": "discord"},
            "calculator":{"win": "calc",            "linux": "gnome-calculator"},
            "camera":    {"win": "microsoft.windows.camera:", "linux": "cheese"},
            "settings":  {"win": "ms-settings:",    "linux": "gnome-control-center"},
            "task_manager": {"win": "taskmgr",      "linux": "gnome-system-monitor"},
        }
        
        os_key = "win" if platform.system() == "Windows" else "linux"
        
        cmd = APP_ALIASES.get(app.lower(), {}).get(os_key)
        if not cmd:
            cmd = app
        
        try:
            if platform.system() == "Windows":
                if os.path.exists(cmd):
                    os.startfile(cmd)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(f"start {cmd}", shell=True)
            else:
                subprocess.Popen([cmd], start_new_session=True)
            
            return ToolResult(success=True, data={"launched": app, "command": cmd})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CodeRunTool(BaseTool):
    name = "code_run"
    description = "Execute a shell command or run a code file. Use for: running python scripts, npm commands, git operations, terminal commands."
    security_level = SecurityLevel.DANGEROUS

    def __init__(self, bus=None):
        self.bus = bus

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to run"},
                "cwd": {"type": "string", "description": "Directory to run in (optional)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"}
            },
            "required": ["command"]
        }

    async def execute(self, command: str, cwd: str = None, timeout: int = 30, **kwargs) -> ToolResult:  # type: ignore[override]
        BLOCKED = ["rm -rf /", "format c:", "del /s /q c:\\", ":(){ :|:& };:"]
        if any(b in command.lower() for b in BLOCKED):
            return ToolResult(success=False, error="Blocked: dangerous command pattern")
        
        try:
            target_cwd = cwd or str(Path.home())
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=target_cwd
            )
            
            start_time = time.time()
            output_lines = []
            while True:
                if process.stdout is None:
                    break
                
                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                if remaining <= 0:
                    if self.bus:
                        await self.bus.emit("ws.send", {
                            "type": "terminal_line",
                            "line": f"[Timeout after {timeout}s]",
                            "command": command
                        })
                    process.terminate()
                    break
                    
                try:
                    line_bytes = await asyncio.wait_for(process.stdout.readline(), timeout=remaining)
                except asyncio.TimeoutError:
                    if self.bus:
                        await self.bus.emit("ws.send", {
                            "type": "terminal_line",
                            "line": f"[Timeout after {timeout}s]",
                            "command": command
                        })
                    process.terminate()
                    break

                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8', errors='replace').rstrip()
                output_lines.append(line)
                
                if self.bus:
                    await self.bus.emit("ws.send", {
                        "type": "terminal_line",
                        "line": line,
                        "command": command
                    })
            
            await process.wait()
            
            if self.bus:
                await self.bus.emit("ws.send", {
                    "type": "terminal_exit",
                    "returncode": process.returncode
                })
            
            return ToolResult(success=True, data={
                "stdout": "\n".join(output_lines[-50:]),
                "returncode": process.returncode,
                "command": command
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileSystemTool(BaseTool):
    name = "filesystem"
    description = "Read files, list directories, search for files, create files. For reading code, configs, logs. NOT for deleting."
    security_level = SecurityLevel.READ

    def get_security_level(self, action: str, **kwargs: Any) -> SecurityLevel:
        if action == "write":
            return SecurityLevel.DANGEROUS
        return SecurityLevel.READ

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "read", "search", "write"]},
                "path": {"type": "string", "description": "Target path"},
                "query": {"type": "string", "description": "Search query pattern (for search)"},
                "content": {"type": "string", "description": "Content to write (for write action)"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, path: str = None, query: str = None, content: str = None, **kwargs) -> ToolResult:  # type: ignore[override]
        # Override security_level dynamically if writing
        pass

        base_path = Path.home()
        target = Path(path).expanduser() if path else base_path
        
        # Enforce home directory boundary
        try:
            target = target.resolve()
            if not str(target).startswith(str(base_path.resolve())):
                return ToolResult(success=False, error="Path outside home directory not allowed.")
        except Exception:
            return ToolResult(success=False, error="Invalid path")

        try:
            if action == "list":
                if not target.is_dir():
                    return ToolResult(success=False, error="Path is not a directory")
                
                items = list(target.iterdir())[:50]
                files = [f.name for f in items if f.is_file()]
                dirs = [d.name for d in items if d.is_dir()]
                return ToolResult(success=True, data={"files": files, "dirs": dirs, "path": str(target)})
            
            elif action == "read":
                if not target.is_file():
                    return ToolResult(success=False, error="File not found")
                
                if target.suffix.lower() in [".exe", ".dll", ".bin", ".so", ".o"]:
                    return ToolResult(success=False, error="Binary files not supported")
                
                size = target.stat().st_size
                with open(target, 'r', encoding='utf-8', errors='replace') as f:
                    file_content = f.read(50000)
                
                return ToolResult(success=True, data={
                    "content": file_content + ("\n...[TRUNCATED]" if size > 50000 else ""),
                    "size": size,
                    "path": str(target)
                })
            
            elif action == "search":
                if not query:
                    return ToolResult(success=False, error="Query required for search")
                search_root = str(target) + "/**/" + query
                matches = glob.glob(search_root, recursive=True)
                results = []
                for m in matches[:20]:
                    p = Path(m)
                    if p.is_file():
                        results.append({
                            "path": str(p),
                            "size": p.stat().st_size,
                            "modified": p.stat().st_mtime
                        })
                return ToolResult(success=True, data={"matches": results})
            
            elif action == "write":
                if not content:
                    return ToolResult(success=False, error="Content required for write")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return ToolResult(success=True, data={"written": True, "path": str(target), "bytes": len(content)})
            
            else:
                return ToolResult(success=False, error="Unknown action")
                
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ProcessTool(BaseTool):
    name = "process"
    description = "List running processes, get system info, kill a process."
    security_level = SecurityLevel.READ

    def get_security_level(self, action: str, **kwargs: Any) -> SecurityLevel:
        if action == "kill":
            return SecurityLevel.DANGEROUS
        return SecurityLevel.READ

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "info", "kill"]},
                "name": {"type": "string", "description": "Process name to kill"},
                "pid": {"type": "integer", "description": "Process PID to kill"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, name: str = None, pid: int = None, **kwargs) -> ToolResult:  # type: ignore[override]
        try:
            if action == "list":
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
                    try:
                        mem_mb = p.info['memory_info'].rss / (1024 * 1024) if p.info['memory_info'] else 0
                        procs.append({
                            "pid": p.info['pid'],
                            "name": p.info['name'],
                            "cpu_percent": p.info['cpu_percent'],
                            "memory_mb": round(mem_mb, 2),
                            "status": p.info['status']
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
                return ToolResult(success=True, data=procs[:20])
            
            elif action == "info":
                import sys
                mem = psutil.virtual_memory()
                return ToolResult(success=True, data={
                    "cpu": psutil.cpu_percent(interval=0.1),
                    "ram": mem.percent,
                    "ram_used_gb": round(mem.used / (1024**3), 1),
                    "ram_total_gb": round(mem.total / (1024**3), 1),
                    "disk": psutil.disk_usage('/').percent,
                    "processes": len(psutil.pids()),
                    "uptime_seconds": int(time.time() - psutil.boot_time()),
                    "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 2),
                    "platform": sys.platform
                })
            
            elif action == "kill":
                target_proc = None
                if pid:
                    target_proc = psutil.Process(pid)
                elif name:
                    for p in psutil.process_iter(['pid', 'name']):
                        if p.info['name'] and name.lower() in p.info['name'].lower():
                            target_proc = psutil.Process(p.info['pid'])
                            break
                
                if target_proc:
                    target_proc.terminate()
                    return ToolResult(success=True, data={"killed": target_proc.name(), "pid": target_proc.pid})
                return ToolResult(success=False, error="Process not found")
            
            else:
                return ToolResult(success=False, error="Unknown action")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ClipboardTool(BaseTool):
    name = "clipboard"
    description = "Read from or write to the system clipboard."
    security_level = SecurityLevel.WRITE

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["read", "write"]},
                "text": {"type": "string", "description": "Text to write (required for write)"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, text: str = None, **kwargs) -> ToolResult:  # type: ignore[override]
        try:
            if action == "read":
                content = pyperclip.paste()
                return ToolResult(success=True, data={"content": content})
            elif action == "write":
                if text is None:
                    return ToolResult(success=False, error="Text required for write")
                pyperclip.copy(text)
                return ToolResult(success=True, data={"written": True})
            else:
                return ToolResult(success=False, error="Unknown action")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ScreenshotTool(BaseTool):
    name = "screenshot"
    description = "Take a screenshot of the current screen."
    security_level = SecurityLevel.READ

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "save_path": {"type": "string", "description": "Path to save screenshot (optional)"}
            }
        }

    async def execute(self, save_path: str = None, **kwargs) -> ToolResult:
        try:
            with mss.mss() as sct:
                target_path = save_path or str(Path.home() / "screenshot.png")
                filename = sct.shot(output=target_path)
                return ToolResult(success=True, data={
                    "path": filename,
                    "width": sct.monitors[0]["width"],
                    "height": sct.monitors[0]["height"]
                })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
