# Job Agent - Quick Start Guide

Get up and running with Job Agent in under 10 minutes!

## Prerequisites

- Python 3.8+
- MongoDB installed and running
- LaTeX distribution (for PDF generation)
- Google Gemini API key ([Get free key](https://aistudio.google.com/app/apikey))

## Installation

```bash
# 1. Clone and navigate
git clone https://github.com/yourusername/job_agent.git
cd job_agent

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start MongoDB (if not running)
brew services start mongodb-community  # macOS
# OR
sudo systemctl start mongod            # Linux
```

## Setup

### Option 1: Interactive Wizard (Recommended)

```bash
python cli.py setup
```

Follow the prompts to configure everything automatically.

### Option 2: Manual Setup

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # Fill in your details

# Copy resume templates
cp base_resume.json.example base_resume.json
cp info/achievements.txt.example info/achievements.txt

# Edit with your data
nano base_resume.json
nano info/achievements.txt

# Validate
python cli.py validate-config
```

## First Run

```bash
# Start interactive mode
./job-agent interactive

# OR use Python directly
python cli.py interactive
```

## Basic Workflow

```bash
# 1. Fetch jobs (optional - requires LinkedIn/JobRight cookies)
python cli.py fetch-jobs --source both --limit 10

# 2. View fetched jobs
python cli.py list-jobs

# 3. Generate documents (resume + cover letter)
python cli.py generate-docs --interactive

# 4. Apply to jobs
python cli.py apply --interactive

# 5. Check status
python cli.py status
```

## Essential Configuration

Minimum required in `.env`:

```bash
# API Key (REQUIRED)
GEMINI_API_KEY=your_key_here

# Personal Info (REQUIRED)
YOUR_NAME=John Doe
YOUR_EMAIL=john@example.com
YOUR_PHONE=5551234567

# Address (REQUIRED)
STREET_ADDRESS=123 Main St
CITY=New York
STATE=NY
ZIP_CODE=10001

# Profiles (REQUIRED)
YOUR_LINKEDIN_PROFILE_URL=https://linkedin.com/in/johndoe
YOUR_GITHUB_URL=https://github.com/johndoe

# Work Auth (REQUIRED)
WORK_AUTHORIZED=Yes
REQUIRE_SPONSORSHIP=No

# Background (REQUIRED)
YEARS_EXPERIENCE=3
JOB_TITLE_CURRENT=Software Engineer
TECH_STACK=Python, JavaScript, React
```

## Commands Reference

```bash
# Setup & Config
python cli.py setup              # Run setup wizard
python cli.py validate-config    # Check configuration
python cli.py config-info        # View current config

# Job Operations
python cli.py fetch-jobs         # Scrape job listings
python cli.py list-jobs          # View jobs in DB
python cli.py generate-docs      # Create resume/CL
python cli.py apply              # Submit applications
python cli.py status             # View statistics

# Interactive Mode
python cli.py interactive        # Menu-driven interface
./job-agent interactive          # Shortcut
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Config validation failed" | Run `python cli.py setup` |
| "Failed to connect to database" | Start MongoDB: `brew services start mongodb-community` |
| "PDFLaTeX not found" | Install LaTeX distribution |
| "Gemini API error" | Check API key at https://aistudio.google.com |
| "No jobs found" | Configure LinkedIn/JobRight cookies (optional) |

## Next Steps

- Read [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed documentation
- Check [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- Review [README.md](README.md) for full feature list
- See [CLAUDE.md](CLAUDE.md) for architecture details

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/job_agent/issues)
- Logs: Check `logs/cli.log` for detailed errors
- Validation: Run `python cli.py validate-config`

## Safety Tips

- ✅ Never commit `.env` file
- ✅ Use test passwords (not real ones)
- ✅ Review generated PDFs before applying
- ✅ Start with small job batches (5-10)
- ✅ Monitor rate limits on job platforms

---

**Ready?** Run `python cli.py setup` and start automating! 🚀
