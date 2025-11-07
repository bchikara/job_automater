# config.py
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import platform
import yaml

# --- Determine Project Root ---
PROJECT_ROOT_CONFIG = Path(__file__).resolve().parent

# --- Load Configuration from YAML or .env ---
config_yaml_path = PROJECT_ROOT_CONFIG / 'config.yaml'
config_data = {}

# Try loading from YAML first (preferred method)
if config_yaml_path.exists():
    try:
        with open(config_yaml_path, 'r') as f:
            config_data = yaml.safe_load(f) or {}
        print(f"INFO [config.py]: Loaded configuration from {config_yaml_path}")
    except Exception as e:
        print(f"WARN [config.py]: Failed to load config.yaml: {e}")
        config_data = {}

# Fallback to .env if YAML is not available or empty
if not config_data:
    env_path_1 = PROJECT_ROOT_CONFIG / '.env'
    env_path_2 = PROJECT_ROOT_CONFIG.parent / '.env'

    if env_path_1.exists():
        load_dotenv(dotenv_path=env_path_1)
        print(f"INFO [config.py]: Loaded configuration from {env_path_1}")
    elif env_path_2.exists():
        load_dotenv(dotenv_path=env_path_2)
        print(f"INFO [config.py]: Loaded configuration from {env_path_2}")

# Helper function to get config value from YAML or environment variable
def get_config(yaml_path, env_var, default=''):
    """
    Get configuration value from YAML (preferred) or environment variable (fallback).

    Args:
        yaml_path: Dot-notation path in YAML (e.g., 'api.gemini_api_key')
        env_var: Environment variable name
        default: Default value if not found

    Returns:
        Configuration value
    """
    # Try YAML first
    if config_data:
        keys = yaml_path.split('.')
        value = config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                value = None
                break
        if value is not None:
            return value

    # Fallback to environment variable
    return os.getenv(env_var, default)


# --- Secrets ---
LINKEDIN_SESSION_COOKIE = get_config('scraping.linkedin_cookie', 'LINKEDIN_LI_AT_COOKIE')
JOBRIGHT_COOKIE_STRING = get_config('scraping.jobright_cookie', 'JOBRIGHT_COOKIE_STRING')
GEMINI_API_KEY = get_config('api.gemini_api_key', 'GEMINI_API_KEY')
SKYVERN_API_KEY = get_config('api.skyvern_api_key', 'SKYVERN_API_KEY', '')

# --- Database (MongoDB) ---
MONGODB_CONNECTION_STRING = get_config('database.connection_string', 'MONGODB_CONNECTION_STRING', "mongodb://localhost:27017/")
DB_NAME = get_config('database.name', 'DB_NAME', "job_agent_db")

# --- Personal Information ---
# IMPORTANT: Set these in your config.yaml or .env file - no defaults for security!
YOUR_NAME = get_config('personal.full_name', 'YOUR_NAME', '')
FIRST_NAME = get_config('personal.first_name', 'FIRST_NAME', '')
LAST_NAME = get_config('personal.last_name', 'LAST_NAME', '')
YOUR_PHONE = get_config('personal.phone', 'YOUR_PHONE', '')
YOUR_EMAIL = get_config('personal.email', 'YOUR_EMAIL', '')
YOUR_PASSWORD = get_config('credentials.password', 'YOUR_PASSWORD', '')  # For creating accounts on job sites
YOUR_LINKEDIN_URL = get_config('profiles.linkedin', 'YOUR_LINKEDIN_PROFILE_URL', '')
YOUR_GITHUB_URL = get_config('profiles.github', 'YOUR_GITHUB_URL', '')
YOUR_LEETCODE_URL = get_config('profiles.leetcode', 'YOUR_LEETCODE_URL', '')
WEBSITE = get_config('profiles.website', 'WEBSITE', '')
LOCATION = get_config('personal.address.display', 'LOCATION', '')

# --- Address Information ---
STREET_ADDRESS = get_config('personal.address.street', 'STREET_ADDRESS', '')
CITY = get_config('personal.address.city', 'CITY', '')
STATE = get_config('personal.address.state', 'STATE', '')
ZIP_CODE = get_config('personal.address.zip_code', 'ZIP_CODE', '')
FULL_ADDRESS = f"{STREET_ADDRESS}, {CITY}, {STATE}, {ZIP_CODE}" if all([STREET_ADDRESS, CITY, STATE, ZIP_CODE]) else ''

# --- Work Authorization ---
WORK_AUTHORIZED = get_config('work_authorization.authorized', 'WORK_AUTHORIZED', 'Yes')  # Authorized to work in the US
REQUIRE_SPONSORSHIP = get_config('work_authorization.requires_sponsorship', 'REQUIRE_SPONSORSHIP', 'Yes')  # Requires sponsorship

# --- Demographic Information (for EEO forms) ---
GENDER = get_config('demographics.gender', 'GENDER', 'Prefer not to say')
RACE_ETHNICITY = get_config('demographics.race_ethnicity', 'RACE_ETHNICITY', 'Prefer not to say')
VETERAN_STATUS = get_config('demographics.veteran_status', 'VETERAN_STATUS', 'I am not a protected veteran')
DISABILITY_STATUS = get_config('demographics.disability_status', 'DISABILITY_STATUS', 'I do not have a disability')


default_linkedin_text = YOUR_LINKEDIN_URL.replace("https://", "").replace("http://", "").replace("www.", "") if YOUR_LINKEDIN_URL else ""
YOUR_LINKEDIN_URL_TEXT = os.getenv('YOUR_LINKEDIN_URL_TEXT', default_linkedin_text)
default_github_text = YOUR_GITHUB_URL.replace("https://", "").replace("http://", "") if YOUR_GITHUB_URL else ""
YOUR_GITHUB_URL_TEXT = os.getenv('YOUR_GITHUB_URL_TEXT', default_github_text)
default_leetcode_text = YOUR_LEETCODE_URL.replace("https://", "").replace("http://", "") if YOUR_LEETCODE_URL else ""
YOUR_LEETCODE_URL_TEXT = os.getenv('YOUR_LEETCODE_URL_TEXT', default_leetcode_text)

# --- Logging ---
LOG_LEVEL = get_config("advanced.log_level", "LOG_LEVEL", "INFO").upper()
LOG_DIR_NAME = "logs"

# --- Paths ---
BASE_OUTPUT_DIR_NAME = get_config("advanced.output_dirs.documents", "BASE_OUTPUT_DOCS_DIR", "output_documents")
PROCESSED_APPS_DIR_NAME = get_config("advanced.output_dirs.processed", "PROCESSED_APPS_DIR", "processed_applications")

# Define sub-directory names within PROCESSED_APPS_DIR_NAME
# These will be combined with the root path later
SUCCESS_DIR_NAME = "success"
FAILURE_DIR_NAME = "failure"
EASY_APPLY_DIR_NAME = "easy_apply"

# --- AI Configuration ---
# Use gemini-2.5-flash-lite (latest, fast, high rate limits)
# Note: If you hit rate limits, the API will return 429 errors
# Available models: gemini-2.5-flash-lite, gemini-1.5-flash, gemini-1.5-pro
GEMINI_MODEL_NAME = get_config('api.gemini_model_name', 'GEMINI_MODEL_NAME', 'gemini-2.5-flash-lite')

# --- JobRight API Configuration ---
JOBRIGHT_API_BASE_URL = 'https://jobright.ai/swan/recommend/list/jobs'
JOBRIGHT_HEADERS = {
    'accept': 'application/json, text/plain, */*', 'accept-language': 'en-US,en;q=0.9',
    'priority': 'u=1, i', 'referer': 'https://jobright.ai/jobs/recommend',
    'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"macOS"', 'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'x-client-type': 'web',
}
JOBRIGHT_MAX_POSITION = int(get_config('advanced.jobright.max_position', 'JOBRIGHT_MAX_POSITION', 100))
JOBRIGHT_POSITION_INCREMENT = int(get_config('advanced.jobright.position_increment', 'JOBRIGHT_POSITION_INCREMENT', 10))
JOBRIGHT_REQUEST_DELAY_SECONDS = float(get_config('advanced.jobright.request_delay_seconds', 'JOBRIGHT_REQUEST_DELAY_SECONDS', 2.0))

# --- LinkedIn Scraper Configuration ---
try:
    from linkedin_jobs_scraper.config import Config as LinkedInConfig
    if LINKEDIN_SESSION_COOKIE: LinkedInConfig.LI_AT_COOKIE = LINKEDIN_SESSION_COOKIE
except ImportError: print("WARN [config.py]: linkedin_jobs_scraper library not found.")
except Exception as e: print(f"WARN [config.py]: Error accessing linkedin_jobs_scraper.config: {e}")

# --- Scraper General Configuration ---
SCRAPER_JOB_LIMIT = int(get_config('scraping.job_limit', 'SCRAPER_JOB_LIMIT', 25))

# --- Output Filenames (for scraper backups) ---
OUTPUT_FILENAME_LINKEDIN = "linkedin_jobs_backup.json"
OUTPUT_FILENAME_JOBRIGHT = "jobright_jobs_backup.json"

# --- Application Workflow ---
MAX_JOBS_TO_PROCESS_PER_RUN = int(get_config('application.max_jobs_per_run', 'MAX_JOBS_TO_PROCESS_PER_RUN', 5))

# Rate limiting between applications (seconds)
# Random delay between MIN and MAX to appear more human-like
# SET TO 0 FOR TESTING - Change back to 30/90 for production
APPLICATION_DELAY_MIN = int(get_config('application.delay.min', 'APPLICATION_DELAY_MIN', 0))
APPLICATION_DELAY_MAX = int(get_config('application.delay.max', 'APPLICATION_DELAY_MAX', 0))

# --- Job Status Constants (CLEANED - No Duplicates) ---
# New/Processing States
JOB_STATUS_NEW = "new"
JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_TAILORING_FAILED = "tailoring_failed"
JOB_STATUS_GENERATION_FAILED = "generation_failed"
JOB_STATUS_DOCS_READY = "docs_ready"

# Application States
JOB_STATUS_APP_PENDING = "application_pending"
JOB_STATUS_APP_IN_PROGRESS = "application_in_progress"

# Success States
JOB_STATUS_APPLIED_SUCCESS = "applied_success"
JOB_STATUS_MANUAL_INTERVENTION_SUBMITTED = "manual_intervention_submitted_by_user"

# Failure States
JOB_STATUS_APP_FAILED_ATS = "application_failed_ats"
JOB_STATUS_APP_FAILED_ATS_STEP = "application_failed_ats_step"
JOB_STATUS_APP_FAILED_UNEXPECTED = "application_failed_unexpected"
JOB_STATUS_APP_FAILED_MANUAL = "application_failed_manual"
JOB_STATUS_MANUAL_INTERVENTION_CLOSED_BY_USER = "manual_intervention_closed_by_user"
JOB_STATUS_MANUAL_INTERVENTION_FAILED = "manual_intervention_failed_by_user"

# Other
JOB_STATUS_APP_SKIPPED = "application_skipped"
JOB_STATUS_ERROR_UNKNOWN = "error_unknown"

# --- Education (for resume generation) ---
UNIVERSITY = get_config('education.university', 'UNIVERSITY', '')
DEGREE = get_config('education.degree', 'DEGREE', '')
EDUCATION_LOCATION = get_config('education.location', 'EDUCATION_LOCATION', '')
EDUCATION_DATES = get_config('education.dates', 'EDUCATION_DATES', '')

# --- Professional Background (for AI-generated answers) ---
YEARS_EXPERIENCE = str(get_config('professional.years_experience', 'YEARS_EXPERIENCE', '0'))
JOB_TITLE_CURRENT = get_config('professional.current_job_title', 'JOB_TITLE_CURRENT', '')
TECH_STACK = get_config('professional.tech_stack', 'TECH_STACK', '')
KEY_ACHIEVEMENT = get_config('professional.key_achievement', 'KEY_ACHIEVEMENT', '')
SPECIALIZATIONS = get_config('professional.specializations', 'SPECIALIZATIONS', '')
SOFT_SKILLS = get_config('professional.soft_skills', 'SOFT_SKILLS', '')
CAREER_PASSION = get_config('professional.career_passion', 'CAREER_PASSION', '')

# --- PDFLaTeX Path (Optional) ---
PDFLATEX_PATH = get_config("advanced.pdflatex_path", "PDFLATEX_PATH", None)
if not PDFLATEX_PATH and platform.system() == "Darwin":
    common_mac_pdflatex_paths = ['/Library/TeX/texbin/pdflatex', '/usr/local/texlive/2025/bin/universal-darwin/pdflatex', '/usr/local/texlive/2024/bin/universal-darwin/pdflatex', '/usr/local/texlive/2023/bin/universal-darwin/pdflatex']
    for p_path in common_mac_pdflatex_paths:
        if os.path.exists(p_path):
            PDFLATEX_PATH = p_path
            break

# --- Explicitly define optional paths (even if None) ---
# This ensures the attribute always exists, even if the env var isn't set
CHROME_EXECUTABLE_PATH = get_config("advanced.chrome.executable_path", "CHROME_EXECUTABLE_PATH", None)
CHROME_DRIVER_PATH = get_config("advanced.chrome.driver_path", "CHROME_DRIVER_PATH", None)
CHROME_USER_DATA_DIR = get_config("advanced.chrome.user_data_dir", "CHROME_USER_DATA_DIR", None)

# --- ** ADDED DEFAULT USER AGENT ** ---
DEFAULT_USER_AGENT = get_config("advanced.user_agent", "DEFAULT_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
# --- ---

# --- Configuration Validation ---
# Validate configuration on import (can be disabled by setting SKIP_CONFIG_VALIDATION=1)
if not os.getenv('SKIP_CONFIG_VALIDATION'):
    try:
        from config_validator import validate_configuration
        # Only validate if we're not in a setup/init context
        if __name__ != '__main__' and 'setup' not in sys.argv and 'config-info' not in sys.argv:
            # Quick validation without verbose output
            validate_configuration(verbose=False, exit_on_error=False)
    except ImportError:
        pass  # config_validator not available yet
    except Exception as e:
        print(f"Warning: Configuration validation failed: {e}")