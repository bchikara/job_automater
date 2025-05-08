# job_automator/ats_fillers/greenhouse_filler.py
import logging
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from .base_filler import BaseFiller, ApplicationError # Import base and custom error
import config # For status constants
from selenium.webdriver.remote.webdriver import WebDriver

class GreenhouseFiller(BaseFiller):
    """Fills job applications on Greenhouse ATS."""
    logger = logging.getLogger(__name__)

    # --- Common Greenhouse Locators (Needs Verification/Adjustment) ---
    LOCATORS = {
        # Basic Info
        "first_name": (By.ID, "first_name"),
        "last_name": (By.ID, "last_name"),
        "email": (By.ID, "email"),
        "phone": (By.ID, "phone"),
        "linkedin_profile": (By.XPATH, "//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'linkedin')]/following-sibling::input"),
        "github_profile": (By.XPATH, "//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'github')]/following-sibling::input"),
        "website": (By.XPATH, "//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'website')]/following-sibling::input"),
        "address": (By.XPATH, "//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'what is your current location')]/following-sibling::input"), # May not always exist
        # Documents
        "resume_input": (By.XPATH, "//input[@id='resume' and @type='file']"),
        "cover_letter_input": (By.XPATH, "//input[@id='cover_letter' and @type='file']"),
        # Custom Questions / EEO
        "custom_questions_section": (By.ID, "custom_fields"),
        "eeo_section": (By.ID, "demographic_questions"), # Common ID for EEO section
        "gender_decline_radio": (By.XPATH, "//label[contains(normalize-space(.), 'decline to self-identify')]/preceding-sibling::input[@name='job_application[gender_demographics_attributes][gender]']"),
        "race_decline_checkbox": (By.XPATH, "//label[contains(normalize-space(.), 'decline to self-identify')]/preceding-sibling::input[contains(@name,'race_demographics')]"), # May be checkbox
        "veteran_decline_radio": (By.XPATH, "//label[contains(normalize-space(.), 'decline to self-identify')]/preceding-sibling::input[contains(@name,'veteran')]"),
        "disability_decline_radio": (By.XPATH, "//label[contains(normalize-space(.), 'No, I do not wish')]/preceding-sibling::input[contains(@name,'disability')]"),
        # Submit
        "submit_button": (By.ID, "submit_app"),
        # Confirmation (Example - needs verification)
        "confirmation_message": (By.XPATH, "//*[contains(normalize-space(.), 'Application Submitted') or contains(normalize-space(.), 'Thank you')]"),
    }

    # --- ADD THIS INIT METHOD ---
    def __init__(self, driver: WebDriver, job_data: dict, user_profile: dict, document_paths: dict, credentials=None):
        """Initializes the Greenhouse Filler."""
        super().__init__(driver, job_data, user_profile, document_paths, credentials)
        self.logger.info(f"{self.log_prefix}Greenhouse Filler Initialized.")
    # --- END OF INIT METHOD ---

    def apply(self) -> str:
        """Orchestrates the Greenhouse application process."""
        self.logger.info(f"{self.log_prefix}Starting Greenhouse application.")
        try:
            if not self.navigate_to_start(): raise ApplicationError("Failed navigation to start URL.")
            time.sleep(2)

            if not self.fill_basic_info(): raise ApplicationError("Failed filling basic info.")
            if not self.upload_documents(): raise ApplicationError("Failed document upload.")
            if not self.answer_custom_questions(): self.logger.warning(f"{self.log_prefix}Custom question handling potentially incomplete.")
            if not self.review_and_submit(): raise ApplicationError("Failed application submission.")

            # --- Confirmation Check ---
            if self.find_element(self.LOCATORS["confirmation_message"], wait_time=10):
                self.logger.info(f"{self.log_prefix}Application submitted successfully (Confirmation message found).")
                return config.JOB_STATUS_APPLIED_SUCCESS
            else:
                # Submit might have worked even without confirmation message
                self.logger.warning(f"{self.log_prefix}Submit clicked, but confirmation message not found. Assuming success with caution.")
                return config.JOB_STATUS_APPLIED_SUCCESS

        except ApplicationError as app_err:
            self.logger.error(f"{self.log_prefix}Application failed: {app_err.message}", exc_info=False) # Log message without full trace often
            return app_err.status # Return specific failure status
        except Exception as e:
             self.logger.error(f"{self.log_prefix}Unexpected error during Greenhouse apply: {e}", exc_info=True)
             return config.JOB_STATUS_APP_FAILED_ATS # Generic failure

    def fill_basic_info(self) -> bool:
        """Fills basic contact information."""
        self.logger.info(f"{self.log_prefix}Filling basic information...")
        # Use self.user_profile data
        profile = self.user_profile
        success = True
        # Use fatal=True for essential fields
        success &= self.type_text(self.LOCATORS["first_name"], profile.get("first_name",""), desc="First Name")
        success &= self.type_text(self.LOCATORS["last_name"], profile.get("last_name",""), desc="Last Name")
        success &= self.type_text(self.LOCATORS["email"], profile.get("email",""), desc="Email")
        success &= self.type_text(self.LOCATORS["phone"], profile.get("phone",""), desc="Phone") # Often optional
        self.type_text(self.LOCATORS["address"], profile.get("address",""), desc="Address") # Optional
        self.type_text(self.LOCATORS["linkedin_profile"], profile.get("linkedin", ""), desc="LinkedIn")
        self.type_text(self.LOCATORS["github_profile"], profile.get("github", ""), desc="GitHub/Website")
        # Add more fields as needed (City, State, ZIP, etc.)
        return success

    def upload_documents(self) -> bool:
        """Uploads resume and cover letter."""
        self.logger.info(f"{self.log_prefix}Uploading documents...")
        # Resume (Mandatory)
        resume_path = self.document_paths.get("resume")
        if not resume_path or not Path(resume_path).is_file():
            raise ApplicationError(f"Resume file not found or invalid path: {resume_path}", config.JOB_STATUS_ERROR_UNKNOWN)

        if self.click_element(self.LOCATORS["resume_attach_button"], desc="Resume Attach Button", wait_time=15):
            if not self.upload_file(self.LOCATORS["resume_input"], resume_path, desc="Resume Input"):
                raise ApplicationError("Failed resume upload (after button click).")
        else: # Fallback if button not clicked/found
            self.logger.warning(f"{self.log_prefix}Resume attach button not clicked, trying direct input.")
            if not self.upload_file(self.LOCATORS["resume_input"], resume_path, desc="Resume Input (Fallback)"):
                raise ApplicationError("Failed resume upload (direct input failed).")
        self.logger.info(f"{self.log_prefix}Resume upload initiated: {Path(resume_path).name}")

        # Cover Letter (Optional)
        cl_path = self.document_paths.get("cover_letter")
        if cl_path and Path(cl_path).is_file():
            # Check if attach button exists first (more reliable)
            if self.find_element(self.LOCATORS["cover_letter_attach_button"], wait_time=3):
                if self.click_element(self.LOCATORS["cover_letter_attach_button"], desc="CL Attach Button", wait_time=5):
                     if not self.upload_file(self.LOCATORS["cover_letter_input"], cl_path, desc="CL Input"):
                          self.logger.warning(f"{self.log_prefix}Failed CL upload after clicking button.")
                     else: self.logger.info(f"{self.log_prefix}Cover Letter upload initiated: {Path(cl_path).name}")
                else: self.logger.warning(f"{self.log_prefix}Found CL attach button but failed to click.")
            # Fallback to direct input if button logic failed or button not found
            elif self.find_element(self.LOCATORS["cover_letter_input"], wait_time=2):
                 if self.upload_file(self.LOCATORS["cover_letter_input"], cl_path, desc="CL Input (Direct)"):
                      self.logger.info(f"{self.log_prefix}Cover Letter upload initiated (direct).")
                 else: self.logger.warning(f"{self.log_prefix}Failed direct CL upload.")
            else: self.logger.info(f"{self.log_prefix}Cover letter section/button not found, skipping.")
        else: self.logger.info(f"{self.log_prefix}No Cover Letter path provided/found, skipping.")

        # Add wait/check for upload completion if Greenhouse provides clear indicator
        time.sleep(4) # Generic wait
        return True

    def answer_custom_questions(self) -> bool:
        self.logger.info(f"{self.log_prefix}Handling custom questions...")
        # --- Attempt to handle common EEO/Demographic questions ---
        self.logger.debug("Attempting to select 'Decline to self-identify' for common demographic questions...")
        eeo_handled = 0
        # Try clicking decline for Gender, Race, Veteran, Disability using common patterns
        if self.click_element(self.LOCATORS["gender_decline_radio"], desc="Gender Decline", wait_time=3): eeo_handled += 1
        if self.click_element(self.LOCATORS["race_decline_checkbox"], desc="Race Decline", wait_time=3): eeo_handled += 1 # Note: might be radio
        if self.click_element(self.LOCATORS["veteran_decline_radio"], desc="Veteran Decline", wait_time=3): eeo_handled += 1
        if self.click_element(self.LOCATORS["disability_decline_radio"], desc="Disability Decline", wait_time=3): eeo_handled += 1
        if eeo_handled > 0: self.logger.info(f"Attempted to decline {eeo_handled} EEO/demographic questions.")

        # --- Placeholder for other questions ---
        # TODO: AI - Find questions by label text
        # TODO: AI - Determine question type (text, radio, select, checkbox)
        # TODO: AI - Generate answer using self.ai_answer_question() for text types
        # TODO: AI - Select appropriate option for multiple choice / dropdown
        # Example:
        # question_locator = (By.XPATH, "//label[contains(.,'work authorization')]/..//select")
        # if self.find_element(question_locator, wait_time=3):
        #     self.select_dropdown_option(question_locator, option_text="Yes", desc="Work Auth") # Requires profile data

        self.logger.info(f"{self.log_prefix}Custom question handling complete (best effort).")
        return True # Return True unless a *required* custom question fails critically

    def review_and_submit(self) -> bool:
        self.logger.info(f"{self.log_prefix}Attempting final submission...")
        # Scroll to bottom first?
        # self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # time.sleep(0.5)
        if self.click_element(self.LOCATORS["submit_button"], desc="Submit Button", wait_time=20):
             time.sleep(5) # Wait for page reaction/confirmation
             return True # Assume success for now, confirmation check in apply()
        else:
             self.logger.error(f"{self.log_prefix}Failed to click the final submit button.")
             # TODO: Check for validation error messages near the button?
             return False