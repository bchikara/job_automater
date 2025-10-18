# job_automator/ats_fillers/workday_filler.py
import logging
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from .base_filler import BaseFiller, ApplicationError
import config
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
    NoSuchFrameException
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

class WorkdayFiller(BaseFiller):
    """
    Fills job applications on Workday ATS. (HIGHLY VARIABLE PER COMPANY)
    Requires significant adaptation and likely AI/dynamic element finding.
    """
    logger = logging.getLogger(__name__)

    # Locators are VERY LIKELY TO CHANGE. Use data-automation-id cautiously.
    LOCATORS = {
        # Initial Step
        "autofill_resume_button": (By.XPATH, "//*[contains(@data-automation-id, 'autofillWithResume')]"),
        "apply_manually_button": (By.XPATH, "//*[contains(@data-automation-id, 'applyManually')]"),
        "create_account_button": (By.XPATH, "//*[contains(@data-automation-id, 'createAccount')]"),
        "sign_in_button": (By.XPATH, "//button[contains(@data-automation-id, 'signIn')]"),
        # Document Upload (often on first/second page)
        "resume_upload_input": (By.XPATH, "//input[@type='file' and contains(@data-automation-id, 'resume')]"),
        "resume_attach_button": (By.XPATH, "//div[contains(@data-automation-id, 'resume')]//button[contains(@data-automation-id, 'selectFile')]"),
        "cover_letter_input": (By.XPATH, "//input[@type='file' and contains(@data-automation-id, 'coverLetter')]"),
        "cover_letter_attach_button": (By.XPATH, "//div[contains(@data-automation-id, 'coverLetter')]//button[contains(@data-automation-id, 'selectFile')]"),
        # My Information Section
        "country_dropdown": (By.XPATH, "//button[@data-automation-id='country']"),
        "country_search": (By.XPATH, "//input[@data-automation-id='searchBox']"),
        "country_option_us": (By.XPATH, "//div[@data-automation-id='promptOption' and @data-automation-label='United States']"), # Example
        "first_name": (By.XPATH, "//input[@data-automation-id='legalNameSection_firstName']"),
        "last_name": (By.XPATH, "//input[@data-automation-id='legalNameSection_lastName']"),
        "address_line1": (By.XPATH, "//input[@data-automation-id='addressSection_addressLine1']"),
        "city": (By.XPATH, "//input[@data-automation-id='addressSection_city']"),
        "state_dropdown": (By.XPATH, "//button[@data-automation-id='state']"),
        "postal_code": (By.XPATH, "//input[@data-automation-id='addressSection_postalCode']"),
        "email": (By.XPATH, "//input[@data-automation-id='email']"),
        "phone_device_type": (By.XPATH, "//button[@data-automation-id='phone-device-type']"), # Example ID
        "phone_number": (By.XPATH, "//input[@data-automation-id='phoneNumber']"),
        # My Experience Section (Often auto-parsed, might need manual add/edit buttons)
        "add_experience_button": (By.XPATH, "//button[@aria-label='Add Work Experience']"),
        "add_education_button": (By.XPATH, "//button[@aria-label='Add Education']"),
        # Navigation
        "next_button": (By.XPATH, "//button[@data-automation-id='nextButton']"),
        "save_and_continue_button": (By.XPATH, "//button[@data-automation-id='saveAndContinueButton']"),
        "submit_button": (By.XPATH, "//button[@data-automation-id='submitButton']"),
        "review_button": (By.XPATH, "//button[@data-automation-id='reviewButton']"),
        # Confirmation
         "confirmation_heading": (By.XPATH, "//h2[contains(text(),'Application Submitted') or contains(text(),'Thank You')]"),
    }

    # --- ADD THIS INIT METHOD ---
    def __init__(self, driver: WebDriver, job_data: dict, user_profile: dict, document_paths: dict, credentials=None):
        """Initializes the Workday Filler."""
        super().__init__(driver, job_data, user_profile, document_paths, credentials)
        self.logger.info(f"{self.log_prefix}Workday Filler Initialized.")
    # --- END OF INIT METHOD ---

    def navigate_to_start(self) -> bool:
        """Navigate to the job application URL"""
        try:
            self.logger.info(f"{self.log_prefix}Navigating to Workday application URL...")
            self.driver.get(self.application_url)
            time.sleep(3)  # Wait for page load
            self.logger.info(f"{self.log_prefix}Successfully navigated to {self.application_url}")
            return True
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Failed to navigate: {e}")
            return False

    def apply(self) -> str:
        """Orchestrates the multi-step Workday application process."""
        self.logger.info(f"{self.log_prefix}Starting Workday application (High Variability Expected).")
        max_steps = 15 # Workday can have many steps
        current_step = 1
        try:
            if not self.navigate_to_start(): raise ApplicationError("Failed navigation.")
            time.sleep(3) # Wait for initial load

            # --- Initial Step ---
            if not self._handle_initial_step(): raise ApplicationError("Failed initial step.")
            logger = logging.getLogger(__name__)

            # --- Multi-step Form Loop ---
            while current_step <= max_steps:
                self.logger.info(f"{self.log_prefix}Attempting Step {current_step}/{max_steps}...")
                # TODO: Implement robust page/section detection (AI needed?)
                # Placeholder: Check for known elements/headers
                if self.find_element(self.LOCATORS["first_name"], wait_time=3):
                    logger.info(f"{self.log_prefix}Processing 'My Information' section...")
                    if not self.fill_basic_info(): raise ApplicationError(f"Failed Basic Info (Step {current_step}).")
                elif self.find_element(self.LOCATORS["add_experience_button"], wait_time=3):
                    logger.info(f"{self.log_prefix}Processing 'My Experience' section...")
                    if not self.fill_experience(): logger.warning(f"{self.log_prefix}Experience filling skipped/failed.")
                elif self.find_element(self.LOCATORS["add_education_button"], wait_time=3):
                    logger.info(f"{self.log_prefix}Processing 'Education' section...")
                    if not self.fill_education(): logger.warning(f"{self.log_prefix}Education filling skipped/failed.")
                elif "question" in self.driver.page_source.lower() or "voluntary" in self.driver.page_source.lower(): # Basic check
                    logger.info(f"{self.log_prefix}Processing 'Questions/Disclosures' section...")
                    if not self.answer_custom_questions(): logger.warning(f"{self.log_prefix}Custom questions skipped/failed.")
                elif self.find_element(self.LOCATORS["review_button"], wait_time=3) or self.find_element(self.LOCATORS["submit_button"], wait_time=3):
                    logger.info(f"{self.log_prefix}Reached 'Review/Submit' stage.")
                    if self.review_and_submit(): return config.JOB_STATUS_APPLIED_SUCCESS
                    else: raise ApplicationError("Final submission failed.")
                else:
                    logger.warning(f"{self.log_prefix}Cannot determine context for Step {current_step}. Attempting to proceed.")
                    # Add wait or check if page is still loading?

                # --- Navigate Next ---
                if self.click_element(self.LOCATORS["next_button"], desc="Next Button", wait_time=10):
                    logger.info(f"{self.log_prefix}Clicked 'Next'. Proceeding to next step.")
                elif self.click_element(self.LOCATORS["save_and_continue_button"], desc="Save & Continue", wait_time=5):
                    logger.info(f"{self.log_prefix}Clicked 'Save & Continue'. Proceeding.")
                else:
                    # Check if maybe we are already on submit page?
                    if self.find_element(self.LOCATORS["submit_button"], wait_time=3):
                        logger.info(f"{self.log_prefix}Submit button found unexpectedly. Attempting submit.")
                        if self.review_and_submit(): return config.JOB_STATUS_APPLIED_SUCCESS
                    raise ApplicationError(f"Cannot find 'Next' or 'Submit' on step {current_step}.")

                time.sleep(4 + current_step * 0.5) # Increase wait time for later steps
                current_step += 1

            raise ApplicationError(f"Exceeded max steps ({max_steps}) without submitting.")

        except ApplicationError as app_err:
            self.logger.error(f"{self.log_prefix}Application failed: {app_err.message}")
            return app_err.status
        except Exception as e:
             self.logger.error(f"{self.log_prefix}Unexpected error during Workday apply: {e}", exc_info=True)
             return config.JOB_STATUS_APP_FAILED_ATS

    def _handle_initial_step(self) -> bool:
        """Handles the common first step: Autofill / Manual / Sign In."""
        # Check for sign-in prompt first? If login implemented, handle here.
        # if self.requires_login(): return self.login()

        # Try autofill or manual apply
        autofill_button = self.find_element(self.LOCATORS["autofill_resume_button"], wait_time=10)
        if autofill_button:
             self.logger.info(f"{self.log_prefix}Attempting 'Autofill with Resume'.")
             if not self.click_element(self.LOCATORS["autofill_resume_button"], desc="Autofill Button"): return False
             time.sleep(1)
             return self.upload_documents(required=True) # Upload is expected after autofill click
        else:
            manual_button = self.find_element(self.LOCATORS["apply_manually_button"], wait_time=3)
            if manual_button:
                 self.logger.info(f"{self.log_prefix}Attempting 'Apply Manually'.")
                 if not self.click_element(self.LOCATORS["apply_manually_button"], desc="Manual Button"): return False
                 # Upload might be on this page or next, try optional upload
                 return self.upload_documents(required=False)
            else:
                 # Assume direct upload/form fields
                 self.logger.info(f"{self.log_prefix}No Autofill/Manual buttons found, proceeding directly.")
                 return self.upload_documents(required=False)

    def fill_basic_info(self) -> bool:
        self.logger.info(f"{self.log_prefix}Filling Workday basic info...")
        success = True
        # Assume fields might be partially filled by resume parse, don't clear initially
        # Use fatal=True only if crashing is better than potentially skipping
        success &= self.type_text(self.LOCATORS["first_name"], self.user_profile.get("first_name",""), desc="First Name", clear_first=False, fatal=False)
        success &= self.type_text(self.LOCATORS["last_name"], self.user_profile.get("last_name",""), desc="Last Name", clear_first=False, fatal=False)
        success &= self.type_text(self.LOCATORS["email"], self.user_profile.get("email",""), desc="Email", clear_first=False, fatal=True) # Email usually mandatory
        # Handle phone type dropdown - highly variable locator
        # if self.click_element(self.LOCATORS["phone_device_type"], desc="Phone Type Dropdown"):
             # self.click_element(self.LOCATORS["phone_device_type_option"], desc="Mobile Option")
        success &= self.type_text(self.LOCATORS["phone_number"], self.user_profile.get("phone",""), desc="Phone Number", clear_first=False)
        # TODO: Handle address fields (country dropdowns, state, city, zip) - complex interaction often needed
        self.logger.warning(f"{self.log_prefix}Address filling needs specific implementation for this Workday instance.")
        return success

    def upload_documents(self, required=True) -> bool:
        self.logger.info(f"{self.log_prefix}Handling document upload...")
        resume_path = self.document_paths.get("resume")
        if not resume_path:
             if required: raise ApplicationError("Resume path missing.", config.JOB_STATUS_ERROR_UNKNOWN)
             else: self.logger.warning(f"{self.log_prefix}Optional resume upload skipped: Path missing."); return True # Skip optional

        # Try clicking button first
        if self.click_element(self.LOCATORS["resume_attach_button"], desc="Resume Upload Button", wait_time=5):
            time.sleep(1)
            if not self.upload_file(self.LOCATORS["resume_upload_input"], resume_path, desc="Resume File Input"):
                if required: raise ApplicationError("Failed resume upload after button click.")
                else: self.logger.warning("Optional resume upload failed after button click."); return False
        elif self.find_element(self.LOCATORS["resume_upload_input"], wait_time=3): # Try direct if button failed/missing
             self.logger.info(f"{self.log_prefix}Resume upload button not found/clicked, trying direct input.")
             if not self.upload_file(self.LOCATORS["resume_upload_input"], resume_path, desc="Resume File Input (Direct)"):
                  if required: raise ApplicationError("Failed resume upload (direct input).")
                  else: self.logger.warning("Optional resume upload failed (direct input)."); return False
        else:
             # Cannot find button or input
             if required: raise ApplicationError("Cannot find resume upload button or input.")
             else: self.logger.warning("Optional resume upload skipped: Cannot find element."); return True

        self.logger.info(f"{self.log_prefix}Resume upload initiated.")
        # TODO: Wait for Workday's upload complete indicator (often tricky)
        time.sleep(8) # Longer generic wait for Workday upload
        return True

    def answer_custom_questions(self) -> bool:
        self.logger.info(f"{self.log_prefix}Handling Workday custom/EEO questions...")
        # Extremely variable - relies heavily on specific instance's questions/locators
        # TODO: Implement logic using self.find_elements to locate question blocks/labels
        # TODO: Use self.type_text, self.click_element, self.select_dropdown_option
        # TODO: Leverage self.ai_answer_question for text-based answers
        self.logger.warning(f"{self.log_prefix}Workday custom question handling requires specific implementation or AI.")
        return True # Assume success/skipped for now

    def review_and_submit(self) -> bool:
        self.logger.info(f"{self.log_prefix}Attempting Workday final review and submit...")
        # TODO: Check for required acknowledgements/checkboxes on review page
        if self.click_element(self.LOCATORS["submit_button"], desc="Final Submit Button", wait_time=25):
             # Wait for confirmation page/message
             try:
                 self.wait.until(EC.presence_of_element_located(self.LOCATORS["confirmation_heading"]))
                 self.logger.info(f"{self.log_prefix}Submission successful (Confirmation heading found).")
                 return True
             except TimeoutException:
                  self.logger.warning(f"{self.log_prefix}Clicked submit, but confirmation heading not found.")
                  # Check current URL?
                  if "viewJob" not in self.driver.current_url: # Basic check if we navigated away
                        self.logger.info(f"{self.log_prefix}Assuming success based on URL change.")
                        return True
                  return False # Treat as failure if no confirmation found
        else:
            self.logger.error(f"{self.log_prefix}Failed to click final Workday submit button.")
            return False