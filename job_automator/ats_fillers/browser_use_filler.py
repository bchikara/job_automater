"""
Browser-Use AI Agent Filler - Intelligent automation using AI vision
Uses persistent browser session via BrowserUseSessionManager
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional
import sys

# Add parent directory to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from browser_use_manager import BrowserUseSessionManager, BROWSER_USE_AVAILABLE
except ImportError:
    try:
        from ..browser_use_manager import BrowserUseSessionManager, BROWSER_USE_AVAILABLE
    except ImportError:
        BROWSER_USE_AVAILABLE = False
        BrowserUseSessionManager = None

import config


class BrowserUseFiller:
    """
    AI-powered job application filler using browser-use library.
    Uses GPT-4 Vision to understand and interact with any job application form.
    """

    def __init__(self, job_data, user_profile, document_paths, credentials=None):
        self.job_data = job_data
        self.user_profile = user_profile
        self.document_paths = document_paths
        self.credentials = credentials
        self.logger = logging.getLogger(__name__)

        job_id = job_data.get('job_id', job_data.get('primary_identifier', 'unknown'))
        self.log_prefix = f"[BrowserUseFiller - JobID: {job_id}] "

        if not BROWSER_USE_AVAILABLE:
            self.logger.error(f"{self.log_prefix}browser-use library not installed!")
            raise ImportError("browser-use library is required. Install: pip install browser-use")

    async def apply_async(self) -> str:
        """
        Apply to job using AI agent (async).
        Uses persistent browser session - browser stays open between applications!
        Returns status string from config.
        """
        try:
            self.logger.info(f"{self.log_prefix}Starting Browser-Use AI agent application...")

            # Get job application URL FIRST (fail fast if missing)
            app_url = self.job_data.get('application_url')
            if not app_url:
                self.logger.error(f"{self.log_prefix}No application URL found")
                return config.JOB_STATUS_APP_FAILED_ATS

            self.logger.info(f"{self.log_prefix}Application URL: {app_url}")

            # Check API key
            if not config.GEMINI_API_KEY:
                self.logger.error(f"{self.log_prefix}GEMINI_API_KEY not configured!")
                return config.JOB_STATUS_APP_FAILED_UNEXPECTED

            # Get or create singleton session manager
            self.logger.info(f"{self.log_prefix}Getting browser session manager...")
            session_manager = BrowserUseSessionManager.get_instance()

            # Initialize browser session if not already done (only happens once!)
            if not session_manager._initialized:
                self.logger.info(f"{self.log_prefix}First application - initializing session manager...")
                if not session_manager.initialize():
                    self.logger.error(f"{self.log_prefix}Failed to initialize session manager")
                    return config.JOB_STATUS_APP_FAILED_UNEXPECTED
                self.logger.info(f"{self.log_prefix}✅ Session manager initialized (browser will be reused for all jobs)")
            else:
                self.logger.info(f"{self.log_prefix}✓ Reusing existing session (job #{session_manager._session_count + 1})")

            # Prepare user information for the agent
            self.logger.info(f"{self.log_prefix}Preparing user information...")
            user_info = self._prepare_user_info()

            # Create detailed task for the AI agent
            self.logger.info(f"{self.log_prefix}Creating agent task...")
            task = self._create_agent_task(user_info)

            # Prepare file paths for upload
            import os
            available_files = []
            resume_path = self.document_paths.get('resume')
            cover_letter_path = self.document_paths.get('cover_letter')

            if resume_path and os.path.exists(resume_path):
                available_files.append(resume_path)
                self.logger.info(f"{self.log_prefix}✓ Resume available for upload: {resume_path}")
            else:
                self.logger.warning(f"{self.log_prefix}⚠ Resume not found: {resume_path}")

            if cover_letter_path and os.path.exists(cover_letter_path):
                available_files.append(cover_letter_path)
                self.logger.info(f"{self.log_prefix}✓ Cover letter available for upload: {cover_letter_path}")
            else:
                self.logger.warning(f"{self.log_prefix}⚠ Cover letter not found: {cover_letter_path}")

            # Create agent using the session manager
            # Browser reuse happens automatically via the shared BrowserProfile!
            self.logger.info(f"{self.log_prefix}Creating agent with {len(available_files)} files...")
            agent = session_manager.create_agent(task, available_files)

            if not agent:
                self.logger.error(f"{self.log_prefix}Failed to create agent")
                return config.JOB_STATUS_APP_FAILED_UNEXPECTED

            self.logger.info(f"{self.log_prefix}✓ Agent created (using persistent browser session)")
            self.logger.info(f"{self.log_prefix}🤖 AI agent starting - navigating to {app_url}")
            self.logger.info(f"{self.log_prefix}📋 Task: Fill application form")
            self.logger.info(f"{self.log_prefix}⏳ Maximum: 50 steps")

            # Run the agent WITH retry logic for timeouts
            self.logger.info(f"{self.log_prefix}Running agent.run(max_steps=50)...")

            max_retries = 2
            result = None
            for attempt in range(max_retries):
                try:
                    result = await agent.run(max_steps=50)
                    self.logger.info(f"{self.log_prefix}✓ Agent.run() completed successfully")
                    break  # Success, exit retry loop

                except Exception as run_err:
                    error_msg = str(run_err).lower()
                    is_timeout = any(keyword in error_msg for keyword in ['timeout', 'timed out', '60 seconds'])

                    if is_timeout and attempt < max_retries - 1:
                        wait_time = 30 * (attempt + 1)  # 30s, 60s
                        self.logger.warning(f"{self.log_prefix}⚠ LLM timeout on attempt {attempt + 1}/{max_retries}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue  # Retry

                    # Final attempt failed or non-timeout error
                    self.logger.error(f"{self.log_prefix}Agent.run() failed: {run_err}", exc_info=True)
                    return config.JOB_STATUS_APP_FAILED_UNEXPECTED
            else:
                # All retries exhausted
                self.logger.error(f"{self.log_prefix}All {max_retries} retry attempts exhausted")
                return config.JOB_STATUS_APP_FAILED_UNEXPECTED

            self.logger.info(f"{self.log_prefix}✅ Agent completed. Result: {result}")

            # Analyze result to determine success
            if self._is_application_successful(result):
                self.logger.info(f"{self.log_prefix}Application successful!")
                return config.JOB_STATUS_APPLIED_SUCCESS
            else:
                self.logger.warning(f"{self.log_prefix}Application may have failed")
                return config.JOB_STATUS_APP_FAILED_ATS

        except Exception as e:
            self.logger.error(f"{self.log_prefix}Browser-Use agent error: {e}", exc_info=True)
            return config.JOB_STATUS_APP_FAILED_UNEXPECTED

    def apply(self) -> str:
        """
        Synchronous wrapper for apply_async.
        Returns status string from config.
        """
        try:
            # Run async function in sync context
            # Always use asyncio.run() - it creates a new event loop if needed
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

    def _create_agent_task(self, user_info: Dict) -> str:
        """Create simple, high-level task for AI agent - let the AI figure out HOW to do it"""

        # Get file paths
        resume_path = user_info.get('resume_path', '')
        cover_letter_path = user_info.get('cover_letter_path', '')

        # Get job context
        job_title = self.job_data.get('job_title', 'this position')
        company_name = self.job_data.get('company_name', 'this company')

        task = f"""
Apply to the {job_title} position at {company_name}.

Application URL: {self.job_data.get('application_url')}

Your Information:
- Name: {user_info['first_name']} {user_info['last_name']}
- Email: {user_info['email']}
- Phone: {user_info['phone']}
- Location: {user_info['city']}, {user_info['state']} {user_info['zip_code']}
- LinkedIn: {user_info['linkedin']}
- GitHub: {user_info.get('github', '')}
- Resume: {resume_path}
- Work Authorization: {user_info['work_authorized']}
- Require Sponsorship: {user_info['require_sponsorship']}
- Years of Experience: {config.YEARS_EXPERIENCE}
- Current Title: {config.JOB_TITLE_CURRENT}

Instructions:
1. Navigate to the application URL
2. Click the apply button to start
3. Fill out the entire application form with the information above
4. Upload the resume when asked
5. For demographic questions (gender, race, veteran status, disability), select "Prefer not to answer" if available
6. Submit the application when complete

Complete the application and confirm it was submitted successfully.
"""
        return task

    def _is_application_successful(self, result) -> bool:
        """
        Analyze agent result to determine if application was successful.
        Look for success indicators in the result.
        """
        if not result:
            return False

        result_str = str(result).lower()

        # Success indicators
        success_keywords = [
            'application submitted',
            'successfully submitted',
            'thank you for applying',
            'application received',
            'application complete',
            'confirmation',
            'we have received your application'
        ]

        # Failure indicators
        failure_keywords = [
            'error',
            'failed',
            'could not submit',
            'unable to',
            'captcha',
            'verification required'
        ]

        # Check for failure first
        for keyword in failure_keywords:
            if keyword in result_str:
                return False

        # Check for success
        for keyword in success_keywords:
            if keyword in result_str:
                return True

        # If unclear, assume failure (conservative)
        return False


# Export for use in automator
__all__ = ['BrowserUseFiller', 'BROWSER_USE_AVAILABLE']
