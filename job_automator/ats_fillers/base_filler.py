# job_automator/ats_fillers/base_filler.py
import logging
import time
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
    NoSuchFrameException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select # For dropdowns

# Project imports
# Ensure project root is findable if running this file directly
try:
    import config
    from ..intelligence.llm_clients import get_llm_client # Use relative import
except ImportError:
    # Fallback for direct execution/testing if needed
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    import config
    from job_automator.intelligence.llm_clients import get_llm_client


class ApplicationError(Exception):
    """Custom exception for application failures."""
    def __init__(self, message, status=config.JOB_STATUS_APP_FAILED_ATS):
        self.message = message
        self.status = status
        super().__init__(self.message)

class BaseFiller(ABC):
    """Abstract Base Class for ATS application fillers."""

    MAX_RETRIES = 2 # Max retries for flaky actions

    def __init__(self, driver: WebDriver, job_data: dict, user_profile: dict, document_paths: dict, credentials=None):
        self.driver = driver
        self.job_data = job_data
        self.user_profile = user_profile
        self.document_paths = document_paths
        self.credentials = credentials
        self.logger = logging.getLogger(self.__class__.__name__) # Logger uses subclass name
        self.wait = WebDriverWait(driver, 20) # Standard wait
        self.short_wait = WebDriverWait(driver, 7) # Shorter wait

        self.ats_url = job_data.get('application_url', '')
        self.primary_id = job_data.get('primary_identifier', 'Unknown')
        self.log_prefix = f"[{self.primary_id}][{self.__class__.__name__}] "

        self.llm = get_llm_client()


    def navigate_to_start(self) -> bool: # <--- ENSURE THIS METHOD EXISTS
        """Navigates to the initial application URL."""
        return self.navigate(self.ats_url)

    # --- Abstract Methods ---
    @abstractmethod
    def apply(self) -> str:
        """ Main orchestration method. Must return a config.JOB_STATUS_* string. """
        pass

    @abstractmethod
    def fill_basic_info(self) -> bool:
        """ Fills name, email, phone, address, links etc. Returns True on success. """
        pass

    @abstractmethod
    def upload_documents(self) -> bool:
        """ Handles resume and cover letter upload. Returns True on success. """
        pass

    @abstractmethod
    def answer_custom_questions(self) -> bool:
        """ Handles ATS-specific questions. Returns True if successful or skipped. """
        self.logger.info(f"{self.log_prefix}Default: Skipping custom questions.")
        return True

    @abstractmethod
    def review_and_submit(self) -> bool:
        """ Handles final review and submission. Returns True on success. """
        pass

    # --- Optional Methods (Override if needed) ---
    def requires_login(self) -> bool: return False
    def login(self) -> bool:
        if not self.requires_login(): return True
        self.logger.warning(f"{self.log_prefix}Login required but not implemented."); return False
    def fill_experience(self) -> bool: self.logger.debug(f"{self.log_prefix}Default: Skipping experience filling."); return True
    def fill_education(self) -> bool: self.logger.debug(f"{self.log_prefix}Default: Skipping education filling."); return True

    # --- Common Helper Methods ---
    def navigate(self, url: str) -> bool:
        try:
            self.logger.info(f"{self.log_prefix}Navigating to: {url}"); self.driver.get(url); time.sleep(1.5)
            page_title = self.driver.title.lower()
            if "404" in page_title or "not found" in page_title or "error" in page_title: raise WebDriverException(f"Page title indicates error: '{self.driver.title}'")
            self.logger.info(f"{self.log_prefix}Navigation successful. URL: {self.driver.current_url}")
            return True
        except Exception as e: self.logger.error(f"{self.log_prefix}Navigation error to {url}: {e}", exc_info=True); return False

    def find_element(self, locator: tuple, wait_time=15, fatal=False, desc="") -> WebElement | None:
        by, value = locator; description = f"'{desc}' {locator}" if desc else f"{locator}"; self.logger.debug(f"{self.log_prefix}Finding {description}...")
        try: return WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located(locator))
        except (TimeoutException, NoSuchElementException) as e:
            log_msg = f"{self.log_prefix}Element not found/timeout {description} after {wait_time}s"
            if fatal: self.logger.error(log_msg); raise ApplicationError(f"Required element {description} not found.")
            else: self.logger.warning(log_msg); return None
        except Exception as e:
             log_msg = f"{self.log_prefix}Error finding {description}: {e}"; self.logger.error(log_msg, exc_info=True)
             if fatal: raise ApplicationError(f"Error finding required element {description}.")
             else: return None

    def find_elements(self, locator: tuple, wait_time=5) -> list[WebElement]:
        by, value = locator; self.logger.debug(f"{self.log_prefix}Finding elements {locator}...")
        try: return WebDriverWait(self.driver, wait_time).until(EC.presence_of_all_elements_located(locator))
        except TimeoutException: self.logger.debug(f"{self.log_prefix}No elements found/timeout for {locator}"); return []
        except Exception as e: self.logger.error(f"{self.log_prefix}Error finding elements {locator}: {e}", exc_info=True); return []

    def click_element(self, locator: tuple, desc="", wait_time=10, retry=MAX_RETRIES) -> bool:
        description = f"'{desc}' {locator}" if desc else f"{locator}"; last_exception = None
        for attempt in range(retry + 1):
            try:
                element = WebDriverWait(self.driver, wait_time).until(EC.presence_of_element_located(locator))
                clickable_element = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(locator))
                self.driver.execute_script("arguments[0].click();", clickable_element) # JS Click
                self.logger.info(f"{self.log_prefix}Clicked {description} (via JS)."); time.sleep(0.8 + (attempt * 0.2)); return True
            except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException, TimeoutException) as e_interact:
                 last_exception = e_interact; self.logger.warning(f"{self.log_prefix}Click attempt {attempt+1} failed for {description}: {type(e_interact).__name__}. Retrying..."); time.sleep(1 + attempt)
            except Exception as e: last_exception = e; self.logger.error(f"{self.log_prefix}Error clicking {description} (Attempt {attempt+1}): {e}", exc_info=True); time.sleep(1 + attempt)
        self.logger.error(f"{self.log_prefix}Failed to click {description} after {retry+1} attempts. LastError: {last_exception}"); return False

    def type_text(self, locator: tuple, text: str, desc="", wait_time=10, clear_first=True, retry=MAX_RETRIES) -> bool:
        description = f"'{desc}' {locator}" if desc else f"{locator}";
        if text is None: self.logger.debug(f"{self.log_prefix}Skipping typing for {description} (text is None)."); return True
        last_exception = None
        for attempt in range(retry + 1):
             element = self.find_element(locator, wait_time, desc=desc)
             if not element:
                 if attempt == retry: self.logger.error(f"{self.log_prefix}Failed find {description} for typing."); return False
                 time.sleep(0.5 + attempt); continue
             try:
                 WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located(locator))
                 if clear_first:
                     if sys.platform == 'darwin': element.send_keys(Keys.COMMAND, "a") # Cmd+A on Mac
                     else: element.send_keys(Keys.CONTROL, "a") # Ctrl+A
                     element.send_keys(Keys.DELETE); time.sleep(0.2)
                 element.send_keys(text)
                 self.logger.info(f"{self.log_prefix}Typed text into {description}."); time.sleep(0.3); return True
             except (StaleElementReferenceException, ElementNotInteractableException, TimeoutException) as e_interact:
                  last_exception = e_interact; self.logger.warning(f"{self.log_prefix}Interaction error typing {description} (Attempt {attempt+1}): {type(e_interact).__name__}. Retrying..."); time.sleep(1 + attempt)
             except Exception as e: last_exception = e; self.logger.error(f"{self.log_prefix}Error typing {description} (Attempt {attempt+1}): {e}", exc_info=True); time.sleep(1 + attempt)
        self.logger.error(f"{self.log_prefix}Failed type {description} after {retry+1} attempts. LastError: {last_exception}"); return False

    def select_dropdown_option(self, select_locator: tuple, option_text: str = None, option_value: str = None, desc="") -> bool:
        description = f"'{desc}' {select_locator}" if desc else f"{select_locator}"
        if not option_text and not option_value: self.logger.warning(f"{self.log_prefix}No text/value provided for dropdown {description}."); return False
        select_element = self.find_element(select_locator, desc=f"dropdown {desc}")
        if not select_element: return False
        try:
            select = Select(select_element)
            target_option = option_text or option_value # For logging
            if option_text: select.select_by_visible_text(option_text)
            elif option_value: select.select_by_value(option_value)
            self.logger.info(f"{self.log_prefix}Selected '{target_option}' in dropdown {description}."); time.sleep(0.5); return True
        except NoSuchElementException: self.logger.error(f"{self.log_prefix}Option '{option_text or option_value}' not found in {description}."); return False
        except Exception as e: self.logger.error(f"{self.log_prefix}Error selecting {description}: {e}", exc_info=True); return False

    def upload_file(self, file_input_locator: tuple, file_path: str | Path, desc="") -> bool:
        description = f"'{desc}' {file_input_locator}" if desc else f"{file_input_locator}"
        element = self.find_element(file_input_locator, wait_time=10, desc=f"file input {desc}") # Wait a bit longer
        if not element: self.logger.error(f"{self.log_prefix}File input {description} not found."); return False
        file_path_obj = Path(file_path) if file_path else None
        if not file_path_obj or not file_path_obj.is_file():
            raise ApplicationError(f"Required file not found: {file_path}", config.JOB_STATUS_ERROR_UNKNOWN)
        try:
            abs_path = str(file_path_obj.resolve()); element.send_keys(abs_path)
            self.logger.info(f"{self.log_prefix}Sent file path '{file_path_obj.name}' to input {description}"); time.sleep(2); return True
        except ElementNotInteractableException: self.logger.error(f"{self.log_prefix}File input {description} not interactable. Needs preceding click?"); return False
        except Exception as e: self.logger.error(f"{self.log_prefix}Error uploading file via {description}: {e}", exc_info=True); return False

    # --- IFrame Handling ---
    def switch_to_iframe(self, locator: tuple | str | WebElement, wait_time=15) -> bool:
        """ Switches WebDriver focus to an iframe. """
        self.logger.info(f"{self.log_prefix}Attempting switch to iframe: {locator}")
        try: WebDriverWait(self.driver, wait_time).until(EC.frame_to_be_available_and_switch_to_it(locator)); self.logger.info(f"{self.log_prefix}Switched to iframe."); time.sleep(0.5); return True
        except (TimeoutException, NoSuchFrameException) as e: self.logger.error(f"{self.log_prefix}Failed switch to iframe {locator}: {type(e).__name__}"); return False
        except Exception as e: self.logger.error(f"{self.log_prefix}Error switching iframe {locator}: {e}", exc_info=True); return False

    def switch_to_default_content(self):
        """ Switches focus back to the main page content. """
        try: self.logger.debug(f"{self.log_prefix}Switching to default content."); self.driver.switch_to.default_content(); time.sleep(0.5); return True
        except Exception as e: self.logger.error(f"{self.log_prefix}Error switching to default content: {e}", exc_info=True); return False

    # --- AI Integration Placeholders ---
    def ai_get_field_value(self, field_label: str) -> str | None:
        """Uses AI to determine the value for a given field label based on profile/job data."""
        self.logger.warning(f"{self.log_prefix}AI get field value for '{field_label}' - NOT IMPLEMENTED.")
        # Example call: return field_mapper.map_data_to_field_ai(field_label, self.user_profile, self.job_data)
        return None

    def ai_answer_question(self, question_text: str) -> str:
         """Uses AI to generate an answer for a custom question."""
         self.logger.info(f"{self.log_prefix}Generating AI answer for: '{question_text[:60]}...'")
         if not self.llm: return "Not Available (LLM Error)"
         try:
             # TODO: Construct a better prompt with more context
             prompt = f"Answer the following job application question concisely and professionally, based on standard software engineering qualifications:\nQuestion: {question_text}\nAnswer:"
             response = self.llm.invoke(prompt)
             answer = getattr(response, 'content', '')
             self.logger.info(f"{self.log_prefix}Generated AI answer snippet: {answer[:60]}...")
             return answer or "Not Applicable." # Return something even if empty
         except Exception as e:
             self.logger.error(f"{self.log_prefix}LLM invocation failed for question: {e}")
             return "Error generating answer."