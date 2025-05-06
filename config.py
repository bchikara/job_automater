# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Secrets ---
LINKEDIN_SESSION_COOKIE = os.getenv('LINKEDIN_LI_AT_COOKIE')
JOBRIGHT_COOKIE_STRING = os.getenv('JOBRIGHT_COOKIE_STRING')
MONGODB_CONNECTION_STRING = "mongodb://localhost:27017/"
DB_NAME = os.getenv('DB_NAME', "job_agent_db")
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
BASE_RESUME_PDF_PATH = os.getenv('BASE_RESUME_PDF_PATH', 'Bhupesh_Resume.pdf') # Default filename
print(f"DEBUG [config.py]: MONGODB_CONNECTION_STRING loaded as: {repr(MONGODB_CONNECTION_STRING)}")

# --- Check required secrets ---
if not LINKEDIN_SESSION_COOKIE:
    raise ValueError("LinkedIn 'li_at' session cookie not found in .env (LINKEDIN_LI_AT_COOKIE)")
if not JOBRIGHT_COOKIE_STRING:
    raise ValueError("JobRight cookie string not found in .env (JOBRIGHT_COOKIE_STRING)")
if not GEMINI_API_KEY:
    raise ValueError("Gemini API Key not found in .env (GEMINI_API_KEY)")
if not os.path.exists(BASE_RESUME_PDF_PATH):
     raise FileNotFoundError(f"Base resume PDF not found at path specified in .env: {BASE_RESUME_PDF_PATH}")


# --- JobRight API Configuration ---
JOBRIGHT_API_BASE_URL = 'https://jobright.ai/swan/recommend/list/jobs'
JOBRIGHT_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-IN,en-US;q=0.9,en;q=0.8',
    'priority': 'u=1, i',
    'referer': 'https://jobright.ai/jobs/recommend', # Generic referer
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"', # Example, might need updates
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"', # Example
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36', # Example
    'x-client-type': 'web',
}
JOBRIGHT_MAX_POSITION = 100 # Reduced limit for testing, adjust as needed
JOBRIGHT_POSITION_INCREMENT = 10
JOBRIGHT_REQUEST_DELAY_SECONDS = 1.5


# --- LinkedIn Scraper Configuration ---
try:
    from linkedin_jobs_scraper.config import Config as LinkedInConfig
    LinkedInConfig.LI_AT_COOKIE = LINKEDIN_SESSION_COOKIE
    print(f"DEBUG: LinkedInConfig.LI_AT_COOKIE set (Length: {len(LinkedInConfig.LI_AT_COOKIE)})")
except ImportError:
    print("WARN: linkedin_jobs_scraper.config not found. LinkedIn scraping might fail.")
except AttributeError:
     print("WARN: Could not set LinkedInConfig.LI_AT_COOKIE.")


# --- Other Configurations ---
CHROME_EXECUTABLE_PATH = None # Optional: Specify path if needed
CHROME_DRIVER_PATH = None     # Optional: Specify path if needed
OUTPUT_FILENAME_LINKEDIN = "linkedin_jobs_auth.json" # Backup JSONs
OUTPUT_FILENAME_JOBRIGHT = "jobright_jobs.json"
LINKEDIN_JOB_LIMIT_PER_QUERY = 5 # Reduced limit for testing

# --- Resume Tailoring Config ---
GEMINI_MODEL_NAME = "gemini-1.5-flash" # Or another suitable model

# --- Document Generation Config ---
OUTPUT_DIRECTORY = "Tailored_Resumes_and_Cover_Letters" # Main output folder

print("Configuration loaded.")

