# job_automator/ats_fillers/base_filler.py

import logging
import time
import json
import sys
from pathlib import Path
from collections import OrderedDict
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Union, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, ElementClickInterceptedException,
    WebDriverException, NoSuchFrameException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select

try:
    import config
    from ..intelligence.llm_clients import get_llm_client
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    import config
    from job_automator.intelligence.llm_clients import get_llm_client

class ApplicationError(Exception):
    """Custom exception for application failures."""
    def __init__(self, message: str, status: str = config.JOB_STATUS_APP_FAILED_ATS):
        self.message = message
        self.status = status
        super().__init__(self.message)

class BaseFiller(ABC):
    """Abstract Base Class with enhanced AI capabilities"""
    
    MAX_RETRIES = 2
    MAX_HTML_CHUNK_SIZE = 10000  # Characters per chunk
    MAX_AI_RETRIES = 3
    MAX_CACHE_SIZE = 10  # Maximum cached analyses
    
    def __init__(self, driver: WebDriver, job_data: dict, user_profile: dict, 
                 document_paths: dict, credentials: Optional[dict] = None):
        self.driver = driver
        self.job_data = job_data
        self.user_profile = user_profile
        self.document_paths = document_paths
        self.credentials = credentials
        self.logger = logging.getLogger(self.__class__.__name__)
        self.wait = WebDriverWait(driver, 20)
        self.short_wait = WebDriverWait(driver, 7)
        self.llm = get_llm_client()
        self._ai_cache = OrderedDict()  # For storing chunked responses with LRU eviction
        self.log_prefix = f"[{job_data.get('primary_identifier', 'Unknown')}][{self.__class__.__name__}] "

    # Required abstract methods
    @abstractmethod
    def fill_basic_info(self) -> bool: pass
    
    @abstractmethod
    def upload_documents(self) -> bool: pass
    
    @abstractmethod
    def answer_custom_questions(self) -> bool: pass
    
    @abstractmethod
    def review_and_submit(self) -> bool: pass

    def _get_safe_profile_json_for_prompt(self) -> str:
        """
        Returns a JSON-serializable string for self.user_profile.
        Derived classes should override this if user_profile contains non-standard JSON types.
        """
        try:
            self.logger.debug(f"{self.log_prefix}BaseFiller: Attempting to get safe JSON for user_profile. Type: {type(self.user_profile)}. Data (first 200 chars): {str(self.user_profile)[:200]}")
            profile_json = json.dumps(self.user_profile)
            self.logger.debug(f"{self.log_prefix}BaseFiller: Successfully serialized user_profile using default json.dumps.")
            return profile_json[:self.MAX_HTML_CHUNK_SIZE] # Ensure it's not too long for prompt
        except TypeError as e:
            self.logger.error(f"{self.log_prefix}BaseFiller: Default json.dumps failed for user_profile. Error: {e}. Derived class should override _get_safe_profile_json_for_prompt.")
            return "{}" # Return empty JSON object as fallback
        
    def _get_safe_job_json_for_prompt(self) -> str:
        """
        Returns a JSON-serializable string for self.job_data.
        Derived classes should override this if job_data contains non-standard JSON types like ObjectId.
        """
        try:
            self.logger.debug(f"{self.log_prefix}BaseFiller: Attempting to get safe JSON for job_data. Type: {type(self.job_data)}. Data (first 200 chars): {str(self.job_data)[:200]}")
            job_json = json.dumps(self.job_data)
            self.logger.debug(f"{self.log_prefix}BaseFiller: Successfully serialized job_data using default json.dumps.")
            return job_json[:self.MAX_HTML_CHUNK_SIZE] # Ensure it's not too long for prompt
        except TypeError as e:
            self.logger.error(f"{self.log_prefix}BaseFiller: Default json.dumps failed for job_data. Error: {e}. Derived class should override _get_safe_job_json_for_prompt.")
            return "{}" # Return empty JSON object as fallback

    def analyze_large_html_with_ai(self, html: str, prompt_template: str, cache_key: Optional[str] = None) -> dict:
        if not html or not prompt_template:
            raise ValueError("HTML content and prompt template must be provided")
            
        if cache_key and cache_key in self._ai_cache:
            self._ai_cache.move_to_end(cache_key)
            return self._ai_cache[cache_key]

        # Escape curly braces in the template first
        safe_template = prompt_template.replace('{', '{{').replace('}', '}}')
        # Then unescape the actual placeholders we want
        safe_template = safe_template.replace('{{profile}}', '{profile}') \
                                    .replace('{{job}}', '{job}') \
                                    .replace('{{chunk}}', '{chunk}') \
                                    .replace('{{summary}}', '{summary}') \
                                    .replace('{{chunk_num}}', '{chunk_num}') \
                                    .replace('{{total_chunks}}', '{total_chunks}')

        chunks = [
            html[i:i + self.MAX_HTML_CHUNK_SIZE] 
            for i in range(0, len(html), self.MAX_HTML_CHUNK_SIZE)
        ]
        
        combined_results = {"fields": [], "sections": []}
        previous_summary = "None"
        
        for i, chunk in enumerate(chunks):
            for attempt in range(self.MAX_AI_RETRIES):
                try:
                    prompt = safe_template.format(
                        chunk=chunk,
                        summary=previous_summary,
                        chunk_num=i+1,
                        total_chunks=len(chunks),
                        profile=self._get_safe_profile_json_for_prompt(),
                        job=self._get_safe_job_json_for_prompt()
                    )
                    
                    response = self.llm.invoke(prompt)
                    result = self._parse_ai_response(response.content)
                    
                    if "fields" in result:
                        combined_results["fields"].extend(result["fields"])
                    if "sections" in result:
                        combined_results["sections"].extend(result["sections"])
                    if "summary" in result:
                        previous_summary = result["summary"]
                    
                    break
                except Exception as e:
                    if attempt == self.MAX_AI_RETRIES - 1:
                        raise ApplicationError(f"AI analysis failed after {self.MAX_AI_RETRIES} attempts: {str(e)}")

        if cache_key:
            self._ai_cache[cache_key] = combined_results
            if len(self._ai_cache) > self.MAX_CACHE_SIZE:
                self._ai_cache.popitem(last=False)
                
        return combined_results

    def _parse_ai_response(self, response: str) -> dict:
        """Parse AI response into structured data with robust error handling"""
        try:
            # Clean response - remove markdown code blocks if present
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:].strip()
            if response.endswith("```"):
                response = response[:-3].strip()
            
            # Handle cases where there might be multiple JSON objects
            # Try parsing the entire response first
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            
            # If that fails, look for the first valid JSON object in the response
            # This handles cases where the AI adds explanatory text
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx+1]
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError as e:
                    self.logger.debug(f"Tried parsing substring but failed: {e}")
            
            # If we still can't parse it, try fixing common issues
            try:
                # Remove any trailing commas that might break parsing
                fixed_response = response.replace(',}', '}').replace(',]', ']')
                parsed = json.loads(fixed_response)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError as e:
                self.logger.debug(f"Tried fixing trailing commas but still failed: {e}")
            
            # Final attempt - extract just the first complete JSON object
            try:
                parsed = json.loads(response[:response.rfind('}')+1])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError as e:
                self.logger.debug(f"Final extraction attempt failed: {e}")
            
            # If all else fails
            raise ValueError(f"Could not find valid JSON in response: {response[:200]}...")

        except Exception as e:
            self.logger.error(f"{self.log_prefix}Failed to parse AI response: {str(e)}\nResponse (first 500 chars): {response[:500]}...")
            raise ApplicationError(f"Invalid AI response format: {str(e)}")
        # --- Optional Methods (Override if needed) ---

    def requires_login(self) -> bool: 
        return False
        
    def login(self) -> bool:
        if not self.requires_login(): 
            return True
        self.logger.warning(f"{self.log_prefix}Login required but not implemented.")
        return False
        
    def fill_experience(self) -> bool: 
        self.logger.debug(f"{self.log_prefix}Skipping experience filling.")
        return True
        
    def fill_education(self) -> bool: 
        self.logger.debug(f"{self.log_prefix}Skipping education filling.")
        return True

    # --- Common Helper Methods ---
    def navigate(self, url: str) -> bool:
        try:
            self.logger.info(f"{self.log_prefix}Navigating to: {url}")
            self.driver.get(url)
            time.sleep(1.5)
            page_title = self.driver.title.lower()
            if any(err in page_title for err in ["404", "not found", "error"]):
                raise WebDriverException(f"Page title indicates error: '{self.driver.title}'")
            self.logger.info(f"{self.log_prefix}Navigation successful. URL: {self.driver.current_url}")
            return True
        except Exception as e: 
            self.logger.error(f"{self.log_prefix}Navigation error to {url}: {e}", exc_info=True)
            return False

    def find_element(self, locator: Tuple[By, str], wait_time: int = 15, 
                    fatal: bool = False, desc: str = "") -> Optional[WebElement]:
        by, value = locator
        description = f"'{desc}' {locator}" if desc else f"{locator}"
        self.logger.debug(f"{self.log_prefix}Finding {description}...")
        try: 
            return WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located(locator)
            )
        except (TimeoutException, NoSuchElementException) as e:
            log_msg = f"{self.log_prefix}Element not found/timeout {description} after {wait_time}s"
            if fatal: 
                self.logger.error(log_msg)
                raise ApplicationError(f"Required element {description} not found.")
            self.logger.warning(log_msg)
            return None
        except Exception as e:
            log_msg = f"{self.log_prefix}Error finding {description}: {e}"
            self.logger.error(log_msg, exc_info=True)
            if fatal: 
                raise ApplicationError(f"Error finding required element {description}.")
            return None

    def find_elements(self, locator: Tuple[By, str], wait_time: int = 5) -> List[WebElement]:
        by, value = locator
        self.logger.debug(f"{self.log_prefix}Finding elements {locator}...")
        try: 
            return WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_all_elements_located(locator)
            )
        except TimeoutException: 
            self.logger.debug(f"{self.log_prefix}No elements found/timeout for {locator}")
            return []
        except Exception as e: 
            self.logger.error(f"{self.log_prefix}Error finding elements {locator}: {e}", exc_info=True)
            return []

    def click_element(self, locator: Tuple[By, str], desc: str = "", 
                     wait_time: int = 10, retry: int = MAX_RETRIES) -> bool:
        description = f"'{desc}' {locator}" if desc else f"{locator}"
        last_exception = None
        for attempt in range(retry + 1):
            try:
                element = WebDriverWait(self.driver, wait_time).until(
                    EC.presence_of_element_located(locator)
                )
                clickable_element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(locator)
                )
                self.driver.execute_script("arguments[0].click();", clickable_element)
                self.logger.info(f"{self.log_prefix}Clicked {description} (via JS).")
                time.sleep(0.8 + (attempt * 0.2))
                return True
            except (StaleElementReferenceException, ElementNotInteractableException, 
                  ElementClickInterceptedException, TimeoutException) as e:
                last_exception = e
                self.logger.warning(
                    f"{self.log_prefix}Click attempt {attempt+1} failed for {description}: {type(e).__name__}. Retrying..."
                )
                time.sleep(1 + attempt)
            except Exception as e: 
                last_exception = e
                self.logger.error(
                    f"{self.log_prefix}Error clicking {description} (Attempt {attempt+1}): {e}", 
                    exc_info=True
                )
                time.sleep(1 + attempt)
        self.logger.error(
            f"{self.log_prefix}Failed to click {description} after {retry+1} attempts. LastError: {last_exception}"
        )
        return False

    def type_text(self, locator: Tuple[By, str], text: str, desc: str = "", 
                 wait_time: int = 10, clear_first: bool = True, 
                 retry: int = MAX_RETRIES, fatal: bool = False) -> bool:
        description = f"'{desc}' {locator}" if desc else f"{locator}"
        if text is None: 
            self.logger.debug(f"{self.log_prefix}Skipping typing for {description} (text is None).")
            return True
            
        last_exception = None
        for attempt in range(retry + 1):
            element = self.find_element(locator, wait_time, desc=desc, fatal=fatal)
            if not element:
                if attempt == retry: 
                    self.logger.error(f"{self.log_prefix}Failed find {description} for typing.")
                    return False
                time.sleep(0.5 + attempt)
                continue
                
            try:
                WebDriverWait(self.driver, 3).until(EC.visibility_of_element_located(locator))
                if clear_first:
                    if sys.platform == 'darwin': 
                        element.send_keys(Keys.COMMAND, "a")  # Cmd+A on Mac
                    else: 
                        element.send_keys(Keys.CONTROL, "a")  # Ctrl+A
                    element.send_keys(Keys.DELETE)
                    time.sleep(0.2)
                element.send_keys(text)
                self.logger.info(f"{self.log_prefix}Typed text into {description}.")
                time.sleep(0.3)
                return True
            except (StaleElementReferenceException, ElementNotInteractableException, 
                  TimeoutException) as e:
                last_exception = e
                self.logger.warning(
                    f"{self.log_prefix}Interaction error typing {description} (Attempt {attempt+1}): {type(e).__name__}. Retrying..."
                )
                time.sleep(1 + attempt)
            except Exception as e: 
                last_exception = e
                self.logger.error(
                    f"{self.log_prefix}Error typing {description} (Attempt {attempt+1}): {e}", 
                    exc_info=True
                )
                time.sleep(1 + attempt)
                
        self.logger.error(
            f"{self.log_prefix}Failed type {description} after {retry+1} attempts. LastError: {last_exception}"
        )
        if fatal:
            raise ApplicationError(f"Failed to type text in {description}")
        return False
    
    def select_dropdown_option(self, select_locator: Tuple[By, str], 
                             option_text: Optional[str] = None, 
                             option_value: Optional[str] = None, 
                             desc: str = "") -> bool:
        description = f"'{desc}' {select_locator}" if desc else f"{select_locator}"
        if not option_text and not option_value: 
            self.logger.warning(f"{self.log_prefix}No text/value provided for dropdown {description}.")
            return False
            
        select_element = self.find_element(select_locator, desc=f"dropdown {desc}")
        if not select_element: 
            return False
            
        try:
            select = Select(select_element)
            target_option = option_text or option_value  # For logging
            if option_text: 
                select.select_by_visible_text(option_text)
            elif option_value: 
                select.select_by_value(option_value)
                
            self.logger.info(f"{self.log_prefix}Selected '{target_option}' in dropdown {description}.")
            time.sleep(0.5)
            return True
        except NoSuchElementException: 
            self.logger.error(f"{self.log_prefix}Option '{option_text or option_value}' not found in {description}.")
            return False
        except Exception as e: 
            self.logger.error(f"{self.log_prefix}Error selecting {description}: {e}", exc_info=True)
            return False

    def upload_file(self, file_input_locator: Tuple[By, str], 
                   file_path: Union[str, Path], desc: str = "", 
                   wait_time: int = 10, fatal: bool = False) -> bool:
        description = f"'{desc}' {file_input_locator}" if desc else f"{file_input_locator}"
        element = self.find_element(file_input_locator, wait_time=wait_time, desc=f"file input {desc}")
        if not element: 
            self.logger.error(f"{self.log_prefix}File input {description} not found.")
            if fatal:
                raise ApplicationError(f"File input {description} not found")
            return False
        
        file_path_obj = Path(file_path) if file_path else None
        if not file_path_obj or not file_path_obj.is_file():
            if fatal:
                raise ApplicationError(f"Required file not found: {file_path}", config.JOB_STATUS_ERROR_UNKNOWN)
            return False
        
        try:
            abs_path = str(file_path_obj.resolve())
            element.send_keys(abs_path)
            self.logger.info(f"{self.log_prefix}Sent file path '{file_path_obj.name}' to input {description}")
            time.sleep(2)  # Brief pause after upload
            return True
        except ElementNotInteractableException:
            self.logger.error(f"{self.log_prefix}File input {description} not interactable. Needs preceding click?")
            if fatal:
                raise ApplicationError(f"File input {description} not interactable")
            return False
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Error uploading file via {description}: {e}", exc_info=True)
            if fatal:
                raise ApplicationError(f"Error uploading file: {e}")
            return False
    
    # --- IFrame Handling ---
    def switch_to_iframe(self, locator: Union[Tuple[By, str], str, WebElement], 
                        wait_time: int = 15) -> bool:
        """Switches WebDriver focus to an iframe."""
        self.logger.info(f"{self.log_prefix}Attempting switch to iframe: {locator}")
        try: 
            WebDriverWait(self.driver, wait_time).until(
                EC.frame_to_be_available_and_switch_to_it(locator)
            )
            self.logger.info(f"{self.log_prefix}Switched to iframe.")
            time.sleep(0.5)
            return True
        except (TimeoutException, NoSuchFrameException) as e: 
            self.logger.error(f"{self.log_prefix}Failed switch to iframe {locator}: {type(e).__name__}")
            return False
        except Exception as e: 
            self.logger.error(f"{self.log_prefix}Error switching iframe {locator}: {e}", exc_info=True)
            return False

    def switch_to_default_content(self) -> bool:
        """Switches focus back to the main page content."""
        try: 
            self.logger.debug(f"{self.log_prefix}Switching to default content.")
            self.driver.switch_to.default_content()
            time.sleep(0.5)
            return True
        except Exception as e: 
            self.logger.error(f"{self.log_prefix}Error switching to default content: {e}", exc_info=True)
            return False

    # --- AI Integration ---
    # Example of what the implementation might start to look like in base_filler.py
    def ai_get_field_value(self, field_label: str) -> Optional[str]:
        """Uses AI to determine the value for a given field label based on profile/job data."""
        self.logger.info(f"{self.log_prefix}AI attempting to find value for field: '{field_label}'")
        if not self.llm:
            self.logger.error(f"{self.log_prefix}LLM not available for ai_get_field_value.")
            return None

        # Construct a prompt. This is highly dependent on your LLM and data structures.
        # You'll need to pass relevant parts of self.user_profile and self.job_data
        prompt = (
            f"Given the user profile: {json.dumps(self.user_profile[:200])}...\n" # Truncate for logging/example
            f"And the job data: {json.dumps(self.job_data[:200])}...\n" # Truncate for logging/example
            f"What is the appropriate value for the form field labeled '{field_label}'?"
            f"If the information is not available or not applicable, respond with 'Not Applicable'."
        )
        try:
            response = self.llm.invoke(prompt)
            answer = getattr(response, 'content', '').strip()
            self.logger.info(f"{self.log_prefix}AI suggested value for '{field_label}': '{answer[:60]}...'")

            if "not applicable" in answer.lower() or not answer: # Basic check
                return None
            return answer
        except Exception as e:
            self.logger.error(f"{self.log_prefix}LLM invocation failed for field '{field_label}': {e}")
            return None

    def ai_answer_question(self, question_text: str) -> str:
        """Uses AI to generate an answer for a custom question."""
        self.logger.info(f"{self.log_prefix}Generating AI answer for: '{question_text[:60]}...'")
        if not self.llm: 
            return "Not Available (LLM Error)"
            
        try:
            prompt = (
                f"Answer the following job application question concisely and professionally, "
                f"based on standard software engineering qualifications:\n"
                f"Question: {question_text}\nAnswer:"
            )
            response = self.llm.invoke(prompt)
            answer = getattr(response, 'content', '')
            self.logger.info(f"{self.log_prefix}Generated AI answer snippet: {answer[:60]}...")
            return answer or "Not Applicable."
        except Exception as e:
            self.logger.error(f"{self.log_prefix}LLM invocation failed for question: {e}")
            return "Error generating answer."