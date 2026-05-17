from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path
import json

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

class GoogleAuth:
    def __init__(self, credentials_path: str, token_path: str):
        self.credentials_path = Path(credentials_path).expanduser()
        self.token_path = Path(token_path).expanduser()
        self._creds: Credentials | None = None
    
    def get_credentials(self) -> Credentials:
        """
        Returns valid credentials.
        - Loads from token file if exists
        - Refreshes if expired
        - Runs OAuth flow if no token (opens browser)
        """
        creds = None
        
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(self.token_path), SCOPES
            )
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Google credentials not found at {self.credentials_path}\n"
                        "Download from Google Cloud Console → APIs & Services → Credentials"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                # Opens browser for OAuth consent
                creds = flow.run_local_server(port=0)
            
            # Save token for next time
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, "w") as f:
                f.write(creds.to_json())
        
        self._creds = creds
        return creds
    
    def is_authenticated(self) -> bool:
        try:
            creds = self.get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False
