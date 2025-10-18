# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Automated Job Application Assistant that uses web automation (Selenium), AI (Google Gemini), and MongoDB to automatically apply for jobs. The system scrapes job listings, tailors resumes/cover letters using AI, generates PDFs, and automatically fills out ATS (Applicant Tracking System) forms.

## Commands

### CLI Interface (Recommended)

The project now has a beautiful CLI interface for easy interaction:

```bash
# Install dependencies
pip install -r requirements.txt

# Interactive mode (recommended for users)
python cli.py interactive
# Or use wrapper: ./job-agent interactive

# Fetch jobs
python cli.py fetch-jobs --source both --limit 50

# List jobs
python cli.py list-jobs --status new

# Generate documents for a job
python cli.py generate-docs --interactive

# Apply to jobs
python cli.py apply --interactive        # Single job
python cli.py apply --batch 5            # Multiple jobs

# View status
python cli.py status

# Configuration info
python cli.py config-info
```

### Legacy Pipeline (main.py)

```bash
# Run the full pipeline (skip scraping by default)
python main.py

# Run with scraping enabled
python main.py --run-scraping

# Override log level
python main.py --log-level DEBUG
```

### Database Setup

Requires MongoDB. Set connection string in `.env`:
```
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/
DB_NAME=job_agent_db
```

### Environment Configuration

Create a `.env` file with required keys (see config.py for all options):
- `GEMINI_API_KEY` - Required for AI features
- `LINKEDIN_LI_AT_COOKIE` - For LinkedIn scraping
- `JOBRIGHT_COOKIE_STRING` - For JobRight scraping
- Personal info: `YOUR_NAME`, `YOUR_EMAIL`, `YOUR_PHONE`, etc.

## Architecture

### CLI vs Pipeline

**CLI (cli.py)** - Interactive, command-based interface:
- Individual operations (fetch, generate, apply)
- Interactive job selection with menus
- Real-time progress indicators
- Better for manual control and learning

**Pipeline (main.py)** - Automated batch processing:
- Runs all phases automatically
- Processes multiple jobs in sequence
- Better for scheduled/cron jobs
- Less user interaction

### Pipeline Flow (main.py & CLI)

The system runs in 3 sequential phases:

1. **Scraping Phase** (optional): Scrapes jobs from LinkedIn and JobRight, stores in MongoDB
2. **Processing Phase**: For jobs with status `new`, `tailoring_failed`, or `generation_failed`:
   - Tailors resume/cover letter using AI (resume_tailor module)
   - Generates PDF documents (document_generator module)
   - Updates status to `docs_ready`
3. **Application Phase**: For jobs with status `docs_ready`:
   - Identifies ATS platform (Greenhouse, Workday, etc.)
   - Automates form filling using Selenium
   - Supports manual intervention if automation fails
   - Moves job folders to success/failure/easy_apply directories

### Key Components

**Database Layer (database.py)**
- MongoDB interface with connection management
- URL normalization for deduplication using `primary_identifier`
- Status tracking with predefined constants in config.py
- Indexes: primary_identifier (unique), status, source_platform, date_scraped

**Job Automator (job_automator/)**
- `automator_main.py`: Orchestrates application attempts, manages folder moves
- `ats_identifier.py`: Pattern-based ATS detection from URLs
- `browser_utils.py`: WebDriver initialization and management
- `ats_fillers/`: Platform-specific form filling implementations
  - `base_filler.py`: Abstract base with AI-powered field analysis
  - `greenhouse_filler.py`: Complete Greenhouse implementation with chunked AI processing
  - `workday_filler.py`: Workday implementation (if exists)

**AI Integration (job_automator/intelligence/)**
- `llm_clients.py`: Gemini LLM client initialization
- Used for: field identification, form analysis, question answering, value generation
- Implements chunked HTML processing for large forms (MAX_HTML_CHUNK_SIZE)

**Resume Tailoring (resume_tailor/)**
- Generates tailored LaTeX documents based on job descriptions
- Returns dict with 'resume' and 'cover_letter' LaTeX strings

**Document Generation (document_generator/)**
- `generator.py`: Converts LaTeX to PDF using pdflatex
- Creates resume, cover letter, and job details PDFs
- Stores in job-specific output directories

### Status Flow

Jobs progress through these statuses (defined in config.py):
```
new → processing → docs_ready → application_in_progress →
  → applied_success (moved to success/)
  → application_failed_ats (moved to failure/)
  → manual_intervention_submitted (moved to success/)
  → manual_intervention_closed_by_user (moved to failure/)
```

Error statuses: `tailoring_failed`, `generation_failed`, `application_failed_ats_step`, `error_unknown`

### Manual Intervention System

When automation fails during application:
1. Browser window stays open
2. Console prompts for user action: 'submitted', 'closed', or 'failed'
3. Status updated based on user response
4. Implemented in `GreenhouseFiller._handle_manual_intervention()`

### AI-Powered Form Filling

The BaseFiller and GreenhouseFiller use AI to:
- Analyze HTML forms in chunks (handles large pages)
- Identify form fields and their locators
- Generate appropriate values from user profile
- Handle EEO questions with "prefer not to say"
- Answer custom questions based on job context

AI responses must be valid JSON between \`\`\`json markers. Locators are stored in `ats_fillers/ai_identified_locators.json` for analysis.

## Important Patterns

**URL Normalization**: URLs are normalized in `database.normalize_url()` to create consistent `primary_identifier` for deduplication. This is critical - don't bypass it.

**Job-Specific Directories**: Each job gets a unique folder: `{company}_{title}_{db_id}` in `output_documents/`. After application, moved to `processed_applications/{success|failure|easy_apply}/`.

**MongoDB ObjectId Handling**: When using job data in AI prompts or JSON serialization, ObjectIds must be converted to strings. See `GreenhouseFiller._safe_serialize()` and `_validate_job_id()`.

**Error Handling in Fillers**:
- Raise `ApplicationError` with appropriate status for expected failures
- Fatal vs non-fatal parameters control whether errors raise exceptions
- Unexpected exceptions trigger manual intervention

**Logging**: Use module-level logger: `logger = logging.getLogger(__name__)`. Log prefix pattern: `f"[{primary_id}] "` for job-specific logs.

## Configuration Notes

**config.py** centralizes all settings:
- Loads from `.env` files (current dir or parent)
- Defines all JOB_STATUS_* constants (don't hardcode status strings)
- Platform detection for pdflatex on macOS
- Default user agent, Chrome paths (optional)
- MAX_JOBS_TO_PROCESS_PER_RUN controls batch size

**utils.py** provides:
- PROJECT_ROOT detection (searches for main.py, .git, pyproject.toml)
- LaTeX escaping for resume generation
- HTML decoding with BeautifulSoup
- Filename sanitization for job folders

## Testing Individual Components

```bash
# Test ATS identification
python -m job_automator.ats_identifier

# Test LLM client
python -m job_automator.intelligence.llm_clients
```

## Development Notes

- Virtual environment in `.venv/` or `venv/` (both present - prefer `.venv/`)
- Output directories are created dynamically - don't commit them
- Logs stored in `logs/` directory
- MongoDB connection is lazy-initialized in database.py
- WebDriver (Chrome) managed by browser_utils.py - cleanup in finally blocks

## ATS Platform Support

Currently implemented:
- **Greenhouse**: Full AI-powered implementation with chunked processing
- **Workday**: Partial implementation (check workday_filler.py)

To add new ATS:
1. Add pattern to `ats_identifier.ATS_PATTERNS`
2. Create filler class extending BaseFiller in `ats_fillers/`
3. Implement required methods: `navigate_to_start()`, `fill_basic_info()`, `upload_documents()`, `answer_custom_questions()`, `review_and_submit()`, `apply()`
4. Add to `ATS_FILLER_MAP` in automator_main.py

## Selenium Best Practices

- Use BaseFiller utility methods: `find_element()`, `click_element()`, `type_text()`, `upload_file()`
- These handle waits, retries, JavaScript fallbacks, scrolling
- Always use WebDriverWait instead of sleep for element interactions
- File inputs: use `upload_file()` which sends keys to hidden inputs
