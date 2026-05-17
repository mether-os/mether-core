# Security Policy

## Supported Versions
| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |
| < 1.0   | ❌        |

## Reporting a Vulnerability

DO NOT open a public GitHub issue for security vulnerabilities.

Email: mayanksharma@example.com with subject "METHER OS Security"

We will respond within 48 hours.

## Known Security Considerations

METHER OS runs locally on your machine. Key points:

1. API keys are stored in .env files — never commit these
2. WhatsApp bridge has full send access — review auto-handle settings
3. Terminal tool can execute shell commands — only use on trusted networks
4. Google OAuth tokens stored in ~/.mether/ — keep this directory private
5. Backend has no authentication by default — do not expose port 8000 publicly
