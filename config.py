# config.py
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import platform

# --- Determine Project Root ---
PROJECT_ROOT_CONFIG = Path(__file__).resolve().parent

# --- Load Environment Variables ---
env_path_1 = PROJECT_ROOT_CONFIG / '.env'
env_path_2 = PROJECT_ROOT_CONFIG.parent / '.env'

if env_path_1.exists():
    load_dotenv(dotenv_path=env_path_1)
    print(f"INFO [config.py]: Loaded .env from {env_path_1}")
elif env_path_2.exists():
    load_dotenv(dotenv_path=env_path_2)
    print(f"INFO [config.py]: Loaded .env from {env_path_2}")
else:
    print(f"WARN [config.py]: .env file not found at {env_path_1} or {env_path_2}")


# --- Secrets ---
LINKEDIN_SESSION_COOKIE = 'AQEDAVqMlrsAzzPNAAABlqzI6AsAAAGW0NVsC00ARMaBux8XNRsACPW2X-kxXUA56cBGL8GdraJnq3xQCA5JrVsbmh7d8xVwcsI-zGkxej_6Nr7AqVX8AdvO9MKAl1IGc9zaaKcJK6HLyB47A3Xjr7Io'
JOBRIGHT_COOKIE_STRING = os.getenv('JOBRIGHT_COOKIE_STRING')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# --- Database (MongoDB) ---
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', "mongodb://localhost:27017/")
DB_NAME = os.getenv('DB_NAME', "job_agent_db")

# --- Personal Information ---
YOUR_NAME = os.getenv('YOUR_NAME', 'Bhupesh Chikara')
YOUR_NAME = os.getenv('YOUR_NAME', 'Bhupesh Chikara')
YOUR_NAME = os.getenv('YOUR_NAME', 'Bhupesh Chikara')
YOUR_PHONE = os.getenv('YOUR_PHONE', '+1-3155757385')
YOUR_EMAIL = os.getenv('YOUR_EMAIL', 'bchikara@syr.edu')
YOUR_LINKEDIN_URL = os.getenv('YOUR_LINKEDIN_PROFILE_URL')
YOUR_GITHUB_URL = os.getenv('YOUR_GITHUB_URL')
YOUR_LEETCODE_URL = os.getenv('YOUR_LEETCODE_URL')
WEBSITE="bchikara.com"
FIRST_NAME="Bhupesh"
LAST_NAME="Chikara"
LOCATION="New York"


default_linkedin_text = YOUR_LINKEDIN_URL.replace("https://", "").replace("http://", "").replace("www.", "") if YOUR_LINKEDIN_URL else ""
YOUR_LINKEDIN_URL_TEXT = os.getenv('YOUR_LINKEDIN_URL_TEXT', default_linkedin_text)
default_github_text = YOUR_GITHUB_URL.replace("https://", "").replace("http://", "") if YOUR_GITHUB_URL else ""
YOUR_GITHUB_URL_TEXT = os.getenv('YOUR_GITHUB_URL_TEXT', default_github_text)
default_leetcode_text = YOUR_LEETCODE_URL.replace("https://", "").replace("http://", "") if YOUR_LEETCODE_URL else ""
YOUR_LEETCODE_URL_TEXT = os.getenv('YOUR_LEETCODE_URL_TEXT', default_leetcode_text)

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR_NAME = "logs"

# --- Paths ---
BASE_OUTPUT_DIR_NAME = os.getenv("BASE_OUTPUT_DOCS_DIR", "output_documents")
PROCESSED_APPS_DIR_NAME = os.getenv("PROCESSED_APPS_DIR", "processed_applications")
BASE_OUTPUT_DIR_NAME = os.getenv("BASE_OUTPUT_DOCS_DIR", "output_documents")
# Directory where processed application folders will be moved
PROCESSED_APPS_DIR_NAME = os.getenv("PROCESSED_APPS_DIR", "processed_applications")

# Define sub-directory names within PROCESSED_APPS_DIR_NAME
# These will be combined with the root path later
SUCCESS_DIR_NAME = "success"
FAILURE_DIR_NAME = "failure"
EASY_APPLY_DIR_NAME = "easy_apply"

# --- AI Configuration ---
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-1.5-flash-latest')

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
JOBRIGHT_MAX_POSITION = int(os.getenv('JOBRIGHT_MAX_POSITION', 100))
JOBRIGHT_POSITION_INCREMENT = int(os.getenv('JOBRIGHT_POSITION_INCREMENT', 10))
JOBRIGHT_REQUEST_DELAY_SECONDS = float(os.getenv('JOBRIGHT_REQUEST_DELAY_SECONDS', 2.0))

# --- LinkedIn Scraper Configuration ---
try:
    from linkedin_jobs_scraper.config import Config as LinkedInConfig
    if LINKEDIN_SESSION_COOKIE: LinkedInConfig.LI_AT_COOKIE = LINKEDIN_SESSION_COOKIE
except ImportError: print("WARN [config.py]: linkedin_jobs_scraper library not found.")
except Exception as e: print(f"WARN [config.py]: Error accessing linkedin_jobs_scraper.config: {e}")

# --- Scraper General Configuration ---
SCRAPER_JOB_LIMIT = int(os.getenv('SCRAPER_JOB_LIMIT', 25))

# --- Output Filenames (for scraper backups) ---
OUTPUT_FILENAME_LINKEDIN = "linkedin_jobs_backup.json"
OUTPUT_FILENAME_JOBRIGHT = "jobright_jobs_backup.json"

# --- Application Workflow ---
MAX_JOBS_TO_PROCESS_PER_RUN = int(os.getenv('MAX_JOBS_TO_PROCESS_PER_RUN', 5))

# --- Job Status Constants ---
JOB_STATUS_NEW = "new"; JOB_STATUS_PROCESSING = "processing"; JOB_STATUS_TAILORING_FAILED = "tailoring_failed"
JOB_STATUS_GENERATION_FAILED = "generation_failed"; JOB_STATUS_DOCS_READY = "docs_ready"; JOB_STATUS_APP_PENDING = "application_pending"
JOB_STATUS_APP_IN_PROGRESS = "application_in_progress"; JOB_STATUS_APPLIED_SUCCESS = "applied_success"
JOB_STATUS_APP_FAILED_ATS = "application_failed_ats"; JOB_STATUS_APP_FAILED_MANUAL = "application_failed_manual"
JOB_STATUS_APP_SKIPPED = "application_skipped"; JOB_STATUS_ERROR_UNKNOWN = "error_unknown"

# --- PDFLaTeX Path (Optional) ---
PDFLATEX_PATH = os.getenv("PDFLATEX_PATH")
if not PDFLATEX_PATH and platform.system() == "Darwin":
    common_mac_pdflatex_paths = ['/Library/TeX/texbin/pdflatex', '/usr/local/texlive/2025/bin/universal-darwin/pdflatex', '/usr/local/texlive/2024/bin/universal-darwin/pdflatex', '/usr/local/texlive/2023/bin/universal-darwin/pdflatex']
    for p_path in common_mac_pdflatex_paths:
        if os.path.exists(p_path):
            PDFLATEX_PATH = p_path
            print(f"INFO [config.py]: Auto-detected pdflatex at {PDFLATEX_PATH}")
            break

# --- Explicitly define optional paths (even if None) ---
# This ensures the attribute always exists, even if the env var isn't set
CHROME_EXECUTABLE_PATH = os.getenv("CHROME_EXECUTABLE_PATH", None)
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH", None)

# --- ** ADDED DEFAULT USER AGENT ** ---
DEFAULT_USER_AGENT = os.getenv("DEFAULT_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
# --- ---

# --- Validation for Critical Settings ---
if not GEMINI_API_KEY:
    print("CRITICAL WARNING: GEMINI_API_KEY is missing. Tailoring features will fail.")

print("INFO [config.py]: Configuration loading complete.")