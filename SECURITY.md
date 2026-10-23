# Security Policy

## Supported Versions

| Version | Supported          |
| :---    | :---               |
| 0.1.x   | :white_check_mark: |

---

## Reporting a Vulnerability

The `ascii-motion` project takes security seriously, particularly around media decoding, file uploads, and subprocess execution.

If you discover a security vulnerability (such as path traversal, shell injection, or unsafe deserialization):

1. **Do not disclose it publicly** on GitHub issues or discussions.
2. Please email the maintainer directly at **daveaddams91@gmail.com** with:
   - A description of the vulnerability.
   - Minimal reproduction steps or proof-of-concept media file.
   - Potential impact assessment.
3. You will receive an acknowledgment within 48 hours and regular updates on remediation progress.

---

## Security Protections Implemented

- **Subprocess Safety**: All FFmpeg invocations use explicit argument arrays (`cmd: list[str]`). Shell interpretation (`shell=True`) is strictly prohibited throughout the codebase.
- **Local Server Isolation**: The FastAPI studio backend binds exclusively to `127.0.0.1` (localhost) by default.
- **Upload Sanitization**: Uploaded files receive sanitized UUID filenames and are stored in isolated temporary directories.
- **HTML Escaping**: Standalone HTML animation files escape all special characters (`<`, `>`, `&`) in character payloads to prevent Cross-Site Scripting (XSS).
- **Zero Remote Telemetry**: Video processing is completely local; no video frames or metadata are transmitted to external services.
