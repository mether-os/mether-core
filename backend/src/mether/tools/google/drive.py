from typing import Any
from pathlib import Path
from mether.tools.base import BaseTool, ToolResult, SecurityLevel
from .base_google import BaseGoogleTool
from googleapiclient.http import MediaFileUpload

class DriveTool(BaseTool, BaseGoogleTool):
    name = "drive"
    description = """
Google Drive tool. Actions:
- search: search files by name/content. params: query, max_results (default 10)
- list: list recent files. params: count (default 10)
- read: read a text file from Drive. params: file_id
- upload: upload a local file to Drive. params: local_path, folder_id (optional)
- info: get file metadata. params: file_id
"""
    security_level = SecurityLevel.WRITE

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["search", "list", "read", "upload", "info"]},
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
                "count": {"type": "integer"},
                "file_id": {"type": "string"},
                "local_path": {"type": "string"},
                "folder_id": {"type": "string"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, **kwargs) -> ToolResult:  # type: ignore[override]
        service = self._service("drive", "v3")
        
        try:
            if action == "list":
                count = kwargs.get("count", 10)
                results = service.files().list(
                    pageSize=count,
                    fields="files(id, name, mimeType, size, modifiedTime, webViewLink)",
                    orderBy="modifiedTime desc"
                ).execute()
                
                files = results.get("files", [])
                return ToolResult(success=True, data={"files": files, "count": len(files)})
            
            elif action == "search":
                query = kwargs["query"]
                max_results = kwargs.get("max_results", 10)
                
                query_escaped = query.replace("'", "\\'")
                drive_query = f"name contains '{query_escaped}' or fullText contains '{query_escaped}'"
                
                results = service.files().list(
                    q=drive_query,
                    pageSize=max_results,
                    fields="files(id, name, mimeType, size, modifiedTime, webViewLink)"
                ).execute()
                
                return ToolResult(success=True, data={
                    "files": results.get("files", []),
                    "query": query
                })
            
            elif action == "read":
                file_id = kwargs["file_id"]
                
                meta = service.files().get(
                    fileId=file_id, fields="name,mimeType"
                ).execute()
                
                mime = meta.get("mimeType", "")
                
                if "google-apps.document" in mime:
                    content = service.files().export(
                        fileId=file_id, mimeType="text/plain"
                    ).execute()
                    text = content.decode("utf-8")[:5000]
                
                elif mime.startswith("text/") or mime == "application/json":
                    content = service.files().get_media(fileId=file_id).execute()
                    text = content.decode("utf-8")[:5000]
                
                else:
                    return ToolResult(success=False, error=f"Cannot read binary file type: {mime}")
                
                return ToolResult(success=True, data={
                    "name": meta["name"],
                    "content": text,
                    "file_id": file_id
                })
            
            elif action == "upload":
                local_path = Path(kwargs["local_path"]).expanduser()
                
                if not local_path.exists():
                    return ToolResult(success=False, error=f"File not found: {local_path}")
                
                file_metadata: dict[str, Any] = {"name": local_path.name}
                if kwargs.get("folder_id"):
                    file_metadata["parents"] = [kwargs["folder_id"]]
                
                media = MediaFileUpload(str(local_path), resumable=True)
                result = service.files().create(
                    body=file_metadata, media_body=media, fields="id,name,webViewLink"
                ).execute()
                
                return ToolResult(success=True, data={
                    "uploaded": True,
                    "name": result["name"],
                    "file_id": result["id"],
                    "link": result.get("webViewLink", "")
                })
            
            elif action == "info":
                file_id = kwargs["file_id"]
                meta = service.files().get(
                    fileId=file_id, fields="*"
                ).execute()
                return ToolResult(success=True, data=meta)
                
            else:
                return ToolResult(success=False, error="Unknown action")
                
        except Exception as e:
            return ToolResult(success=False, error=str(e))
