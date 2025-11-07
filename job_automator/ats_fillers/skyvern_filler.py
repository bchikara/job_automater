"""
Skyvern AI Agent Filler - Intelligent automation using AI vision
Uses Skyvern's computer vision + LLM approach for reliable form filling
"""

import logging
import asyncio
import os
from pathlib import Path
from typing import Dict, Optional
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Load .env file from project root BEFORE importing Skyvern
# Use absolute path to ensure it works from any working directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
env_path = PROJECT_ROOT / '.env'
if env_path.exists():
    # Override=True ensures our .env takes precedence
    load_dotenv(dotenv_path=str(env_path), override=True)
    # Also set the working directory for Skyvern to find the .env
    import os
    os.chdir(str(PROJECT_ROOT))
else:
    print(f"WARNING: .env file not found at {env_path}")

try:
    from skyvern import Skyvern
    SKYVERN_AVAILABLE = True
except ImportError:
    SKYVERN_AVAILABLE = False
    Skyvern = None

import config

# Import browser session manager
sys.path.insert(0, str(PROJECT_ROOT))
try:
    from browser_session_manager import get_session_for_url
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    SESSION_MANAGER_AVAILABLE = False
    get_session_for_url = None


class SkyvernFiller:
    """
    AI-powered job application filler using Skyvern library.
    Uses Vision LLMs + Computer Vision to understand and interact with any job application form.

    Advantages over browser-use:
    - 85.8% success rate on WebVoyager benchmark
    - Resilient to website layout changes
    - Purpose-built for form filling automation
    - Less prone to "getting lost" in multi-step forms
    """

    def __init__(self, job_data, user_profile, document_paths, credentials=None):
        self.job_data = job_data
        self.user_profile = user_profile
        self.document_paths = document_paths
        self.credentials = credentials
        self.logger = logging.getLogger(__name__)

        job_id = job_data.get('job_id', job_data.get('primary_identifier', 'unknown'))
        self.log_prefix = f"[SkyvernFiller - JobID: {job_id}] "

        if not SKYVERN_AVAILABLE:
            self.logger.error(f"{self.log_prefix}Skyvern library not installed!")
            raise ImportError("Skyvern library is required. Install: pip install skyvern")

    async def apply_async(self) -> str:
        """
        Apply to job using Skyvern AI agent (async).
        Returns status string from config.
        """
        try:
            self.logger.info(f"{self.log_prefix}Starting Skyvern AI agent application...")

            # Get job application URL FIRST (fail fast if missing)
            app_url = self.job_data.get('application_url')
            if not app_url:
                self.logger.error(f"{self.log_prefix}No application URL found")
                return config.JOB_STATUS_APP_FAILED_ATS

            self.logger.info(f"{self.log_prefix}Application URL: {app_url}")

            # Prepare user information
            self.logger.info(f"{self.log_prefix}Preparing user information...")
            user_info = self._prepare_user_info()

            # Verify files exist
            resume_path = self.document_paths.get('resume')
            cover_letter_path = self.document_paths.get('cover_letter')

            available_files = []
            if resume_path and os.path.exists(resume_path):
                available_files.append(resume_path)
                self.logger.info(f"{self.log_prefix}✓ Resume available: {resume_path}")
            else:
                self.logger.error(f"{self.log_prefix}Resume not found: {resume_path}")
                return config.JOB_STATUS_ERROR_UNKNOWN

            if cover_letter_path and os.path.exists(cover_letter_path):
                available_files.append(cover_letter_path)
                self.logger.info(f"{self.log_prefix}✓ Cover letter available: {cover_letter_path}")

            # Create detailed prompt for Skyvern
            self.logger.info(f"{self.log_prefix}Creating application prompt...")
            prompt = self._create_application_prompt(user_info, app_url)

            # Initialize Skyvern (local mode with PostgreSQL)
            self.logger.info(f"{self.log_prefix}Initializing Skyvern (local mode with PostgreSQL)...")
            skyvern = Skyvern()  # Uses .env file with DATABASE_STRING

            # Get persistent browser session if available
            browser_session_id = None
            if SESSION_MANAGER_AVAILABLE and get_session_for_url:
                browser_session_id = get_session_for_url(app_url)
                if browser_session_id:
                    self.logger.info(f"{self.log_prefix}🔐 Using persistent browser session: {browser_session_id}")
                else:
                    self.logger.info(f"{self.log_prefix}🆕 No persistent session found, using fresh browser")
            else:
                self.logger.warning(f"{self.log_prefix}⚠️ Session manager not available, using fresh browser")

            self.logger.info(f"{self.log_prefix}🤖 Starting Skyvern agent...")
            self.logger.info(f"{self.log_prefix}📋 Target URL: {app_url}")
            self.logger.info(f"{self.log_prefix}📄 Files: {len(available_files)}")
            self.logger.info(f"{self.log_prefix}⏳ Max steps: 50")

            # Run the task with retry logic
            max_retries = 2
            result = None

            for attempt in range(max_retries):
                try:
                    self.logger.info(f"{self.log_prefix}Attempt {attempt + 1}/{max_retries}...")

                    result = await skyvern.run_task(
                        prompt=prompt,
                        url=app_url,
                        wait_for_completion=True,
                        max_steps=50,
                        browser_session_id=browser_session_id,  # Use persistent session if available
                        # Data extraction schema to get structured results
                        data_extraction_schema={
                            "type": "object",
                            "properties": {
                                "status": {
                                    "type": "string",
                                    "description": "Application status: submitted, failed, or error"
                                },
                                "message": {
                                    "type": "string",
                                    "description": "Details about the application outcome"
                                },
                                "confirmation": {
                                    "type": "string",
                                    "description": "Confirmation number if available"
                                }
                            },
                            "required": ["status", "message"]
                        }
                    )

                    self.logger.info(f"{self.log_prefix}✓ Skyvern task completed")
                    break  # Success

                except Exception as run_err:
                    error_msg = str(run_err).lower()
                    is_timeout = 'timeout' in error_msg or 'timed out' in error_msg

                    if is_timeout and attempt < max_retries - 1:
                        wait_time = 30 * (attempt + 1)
                        self.logger.warning(f"{self.log_prefix}⚠ Timeout on attempt {attempt + 1}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    # Final attempt failed or non-timeout error
                    self.logger.error(f"{self.log_prefix}Skyvern task failed: {run_err}", exc_info=True)
                    return config.JOB_STATUS_APP_FAILED_UNEXPECTED
            else:
                # All retries exhausted
                self.logger.error(f"{self.log_prefix}All {max_retries} retry attempts exhausted")
                return config.JOB_STATUS_APP_FAILED_UNEXPECTED

            # Analyze result
            self.logger.info(f"{self.log_prefix}Analyzing result...")
            self.logger.debug(f"{self.log_prefix}Result: {result}")

            if self._is_application_successful(result):
                self.logger.info(f"{self.log_prefix}✅ Application successful!")
                return config.JOB_STATUS_APPLIED_SUCCESS
            else:
                self.logger.warning(f"{self.log_prefix}❌ Application failed")
                return config.JOB_STATUS_APP_FAILED_ATS

        except Exception as e:
            self.logger.error(f"{self.log_prefix}Skyvern agent error: {e}", exc_info=True)
            return config.JOB_STATUS_APP_FAILED_UNEXPECTED

    def apply(self) -> str:
        """
        Synchronous wrapper for apply_async.
        Returns status string from config.
        """
        try:
            return asyncio.run(self.apply_async())
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Error in sync apply: {e}", exc_info=True)
            return config.JOB_STATUS_APP_FAILED_UNEXPECTED

    def _prepare_user_info(self) -> Dict:
        """Prepare user information for the agent"""
        return {
            'name': self.user_profile.get('name', config.YOUR_NAME),
            'first_name': self.user_profile.get('first_name', config.FIRST_NAME),
            'last_name': self.user_profile.get('last_name', config.LAST_NAME),
            'email': self.user_profile.get('email', config.YOUR_EMAIL),
            'phone': self.user_profile.get('phone', config.YOUR_PHONE),
            'linkedin': self.user_profile.get('linkedin_url', config.YOUR_LINKEDIN_URL),
            'github': self.user_profile.get('github_url', config.YOUR_GITHUB_URL),
            'website': self.user_profile.get('website', config.WEBSITE),
            'location': self.user_profile.get('location', config.LOCATION),
            'address': config.FULL_ADDRESS,
            'street': config.STREET_ADDRESS,
            'city': config.CITY,
            'state': config.STATE,
            'zip_code': config.ZIP_CODE,
            'work_authorized': config.WORK_AUTHORIZED,
            'require_sponsorship': config.REQUIRE_SPONSORSHIP,
            'gender': config.GENDER,
            'race': config.RACE_ETHNICITY,
            'veteran_status': config.VETERAN_STATUS,
            'disability_status': config.DISABILITY_STATUS,
            'resume_path': self.document_paths.get('resume'),
            'cover_letter_path': self.document_paths.get('cover_letter'),
        }

    def _create_application_prompt(self, user_info: Dict, app_url: str) -> str:
        """
        Create comprehensive prompt for Skyvern agent.
        Skyvern uses vision + LLM, so we can be more descriptive than browser-use.
        """
        job_title = self.job_data.get('job_title', 'this position')
        company_name = self.job_data.get('company_name', 'your company')

        # Skyvern handles file uploads automatically if available_file_paths is provided
        # But we still mention them in the prompt for context
        resume_filename = os.path.basename(user_info.get('resume_path', ''))
        cover_letter_filename = os.path.basename(user_info.get('cover_letter_path', '')) if user_info.get('cover_letter_path') else None

        prompt = f"""Navigate to the job application and complete the entire application process for the {job_title} position at {company_name}.

CANDIDATE INFORMATION:
Name: {user_info['first_name']} {user_info['last_name']}
Email: {user_info['email']}
Phone: {user_info['phone']}
Location: {user_info['city']}, {user_info['state']} {user_info['zip_code']}
LinkedIn: {user_info['linkedin']}
GitHub: {user_info['github']}
Website: {user_info['website']}

ADDRESS DETAILS:
Street: {user_info['street']}
City: {user_info['city']}
State: {user_info['state']}
Zip Code: {user_info['zip_code']}

WORK AUTHORIZATION:
Authorized to work: {user_info['work_authorized']}
Requires sponsorship: {user_info['require_sponsorship']}

PROFESSIONAL BACKGROUND:
Current Role: {config.JOB_TITLE_CURRENT}
Years of Experience: {config.YEARS_EXPERIENCE}+
Tech Stack: {config.TECH_STACK}

DOCUMENTS:
Resume: {resume_filename}
{f"Cover Letter: {cover_letter_filename}" if cover_letter_filename else "Cover Letter: Not available"}

IMPORTANT INSTRUCTIONS:
1. Click any "Apply", "Start Application", or similar buttons to begin
2. If login is required, use email: {user_info['email']} and password: {config.YOUR_PASSWORD}
3. Fill ALL required fields with the information provided above:
   - Use FIRST NAME and LAST NAME separately when asked (not full name)
   - Split address correctly: street, city, state, zip
   - Upload resume file when prompted ({resume_filename})
   - Upload cover letter if requested and available
4. For optional demographic questions (gender, race, veteran status, disability):
   - Select "Prefer not to answer" or "I do not want to answer" if available
   - Otherwise, use the values provided: Gender={user_info['gender']}, Race={user_info['race']}, Veteran={user_info['veteran_status']}, Disability={user_info['disability_status']}
5. For start date questions: Use a reasonable date 2-4 weeks from today
6. For salary expectations: Enter "Negotiable" or "Market rate" if optional; if required, research typical range
7. Check ALL consent/agreement boxes that appear
8. Review the application before final submission
9. Click "Submit Application" or equivalent button
10. Wait for confirmation page or message

SUCCESS CRITERIA:
- Application form is completely filled out
- All required documents are uploaded
- Form is successfully submitted
- Confirmation page appears OR success message is displayed

If you encounter errors:
- Read the error messages carefully
- Fix the mentioned fields
- Resubmit the application

After completion, return structured data with:
- status: "submitted" if successful, "failed" if not
- message: Brief description of what happened
- confirmation: Confirmation number or ID if displayed
"""
        return prompt

    def _is_application_successful(self, result) -> bool:
        """
        Analyze Skyvern result to determine if application was successful.
        Skyvern returns structured data, so we can check more reliably.
        """
        if not result:
            self.logger.warning(f"{self.log_prefix}No result from Skyvern")
            return False

        # Try to parse structured data if available
        try:
            # result might be a dict with extracted_data
            if isinstance(result, dict):
                extracted = result.get('extracted_data', {})

                # Check status field from our schema
                status = extracted.get('status', '').lower()
                message = extracted.get('message', '')

                self.logger.info(f"{self.log_prefix}Extracted status: {status}")
                self.logger.info(f"{self.log_prefix}Message: {message}")

                if status == 'submitted':
                    return True
                elif status in ['failed', 'error']:
                    return False

            # Fallback: Check task status
            if hasattr(result, 'status'):
                task_status = str(result.status).lower()
                self.logger.info(f"{self.log_prefix}Task status: {task_status}")

                if 'completed' in task_status or 'success' in task_status:
                    return True

        except Exception as e:
            self.logger.error(f"{self.log_prefix}Error analyzing result: {e}")

        # Convert to string and check for keywords
        result_str = str(result).lower()

        # Success indicators
        success_keywords = [
            'submitted',
            'success',
            'confirmation',
            'thank you',
            'application received',
            'application complete'
        ]

        # Failure indicators
        failure_keywords = [
            'error',
            'failed',
            'unable',
            'could not',
            'captcha',
            'verification required'
        ]

        # Check for failure first
        for keyword in failure_keywords:
            if keyword in result_str:
                self.logger.warning(f"{self.log_prefix}Found failure keyword: {keyword}")
                return False

        # Check for success
        for keyword in success_keywords:
            if keyword in result_str:
                self.logger.info(f"{self.log_prefix}Found success keyword: {keyword}")
                return True

        # If unclear, log and assume failure (conservative)
        self.logger.warning(f"{self.log_prefix}Could not determine success from result")
        return False


# Export for use in automator
__all__ = ['SkyvernFiller', 'SKYVERN_AVAILABLE']
