from googleapiclient.discovery import build
from .auth import GoogleAuth

class BaseGoogleTool:
    """Shared base for all Google tools."""
    
    def __init__(self, auth: GoogleAuth):
        self.auth = auth
    
    def _service(self, name: str, version: str):
        creds = self.auth.get_credentials()
        return build(name, version, credentials=creds)
