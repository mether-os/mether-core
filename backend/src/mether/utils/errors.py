from pydantic import BaseModel

class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: str | None = None

class METHERError(Exception):
    def __init__(self, code: str, message: str, detail: str = None):
        self.code = code
        self.message = message
        self.detail = detail

ERROR_CODES = {
    "LLM_UNAVAILABLE": "LLM proxy is not reachable",
    "TOOL_NOT_FOUND": "Requested tool does not exist",
    "TOOL_EXECUTION_FAILED": "Tool failed during execution",
    "GOOGLE_NOT_AUTHENTICATED": "Google OAuth not completed",
    "WHATSAPP_DISCONNECTED": "WhatsApp bridge is not connected",
    "CONFIRMATION_REQUIRED": "Action requires user confirmation",
    "CONFIRMATION_TIMEOUT": "Confirmation timed out",
}
