# Security Policy

## Supported Versions

Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please do **NOT** open a public issue.

Instead, please email: bhupeshchikara@gmail.com

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive a response within 48 hours. If the issue is confirmed, we will:
1. Release a fix as soon as possible
2. Credit you in the release notes (unless you prefer to remain anonymous)

## Security Best Practices

When using this tool:

1. **Never commit sensitive files**:
   - `.env` files with API keys
   - `config.yaml` with credentials
   - Browser profile data
   - Generated resumes with personal info

2. **Use secure passwords**:
   - Use a unique, disposable password for the `credentials.password` field
   - Never reuse your primary passwords

3. **Protect your API keys**:
   - Keep `GEMINI_API_KEY` secure
   - Don't share your `.env` file
   - Rotate keys if compromised

4. **Review generated content**:
   - Always review AI-generated resumes before submission
   - Check application forms for accuracy

## Data Privacy

This tool stores data locally on your machine:
- MongoDB database (job listings, application history)
- Generated PDF documents
- Browser session data

**We do not collect or transmit your personal data to any external servers** (except for AI API calls to Google Gemini for resume generation).
