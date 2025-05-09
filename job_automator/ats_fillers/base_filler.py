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

# Added import for datetime
from datetime import datetime # timezone can be used for Python 3.11+ for explicit UTC

try:
    import config
    from ..intelligence.llm_clients import get_llm_client
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    import config
    from job_automator.intelligence.llm_clients import get_llm_client

# Path for the locator storage JSON file, relative to base_filler.py
LOCATOR_STORAGE_FILE_PATH = Path(__file__).parent / "ai_identified_locators.json"

class ApplicationError(Exception):
    """Custom exception for application failures."""
    def __init__(self, message: str, status: str = config.JOB_STATUS_APP_FAILED_ATS):
        self.message = message
        self.status = status
        super().__init__(self.message)

class BaseFiller(ABC):
    """Abstract Base Class with enhanced AI capabilities"""
    
    # ... (existing code like __init__, logger, etc.)
    MAX_HTML_CHUNK_SIZE = 50000 # Example, adjust as needed in your config
    MAX_AI_RETRIES = 2
    AI_RETRY_DELAY = 5 # seconds
    CACHE_EXPIRY_SECONDS = 3600 # 1 hour, adjust as needed

    def __init__(self, driver: WebDriver, job_data: Dict, user_profile: Dict, 
                 document_paths: Dict[str, str], credentials: Optional[Dict] = None):
        self.driver = driver
        self.job_data = job_data or {}
        self.user_profile = user_profile or {}
        self.document_paths = document_paths or {}
        self.credentials = credentials or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_prefix = f"[{self.__class__.__name__} - JobID: {self.job_data.get('job_id', 'N/A')}] "
        
        # Initialize LLM client
        self.llm = get_llm_client()
        if not self.llm:
            self.logger.warning(f"{self.log_prefix}LLM client not available. AI functionalities will be limited.")
            
        self._ai_cache = OrderedDict() # Simple in-memory cache


    def _log_ai_locator(self,
                        label: str,
                        locator: List[str], # Expected format: ["type_str", "value_str"]
                        context: str,
                        ats_platform: str,
                        job_id_str: Optional[str] = None):
        """
        Logs an AI-identified locator to a JSON file.
        The locator is expected to be a list like ["id", "some_id"].
        """
        if not (isinstance(locator, (list, tuple)) and len(locator) == 2 and
                isinstance(locator[0], str) and isinstance(locator[1], str)):
            self.logger.warning(f"{self.log_prefix}Invalid locator format for logging: {locator} for label '{label}'. Skipping.")
            return

        # Ensure job_id_str is available
        if job_id_str is None:
            # This fallback is generic; specific fillers should pass a validated job_id
            job_id_str = str(self.job_data.get('job_id', 'unknown_job_id'))


        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z", # UTC timestamp in ISO 8601 format
            "job_id": job_id_str,
            "ats_platform": ats_platform,
            "page_context": context,
            "field_label_or_description": label,
            "locator_type": locator[0].lower(), # Standardize to lowercase
            "locator_value": locator[1],
            "source": "AI-generated"
        }

        try:
            data = []
            if LOCATOR_STORAGE_FILE_PATH.exists() and LOCATOR_STORAGE_FILE_PATH.stat().st_size > 0:
                with open(LOCATOR_STORAGE_FILE_PATH, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        if not isinstance(data, list):
                            self.logger.warning(
                                f"{self.log_prefix}Locator storage file {LOCATOR_STORAGE_FILE_PATH} "
                                f"does not contain a list. Reinitializing."
                            )
                            data = []
                    except json.JSONDecodeError:
                        self.logger.warning(
                            f"{self.log_prefix}Error decoding JSON from {LOCATOR_STORAGE_FILE_PATH}. "
                            f"File might be corrupted. Reinitializing."
                        )
                        data = []
            
            data.append(log_entry)
            
            with open(LOCATOR_STORAGE_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            # self.logger.info(f"{self.log_prefix}Logged AI locator for '{label}' in '{context}' to {LOCATOR_STORAGE_FILE_PATH.name}")

        except IOError as e:
            self.logger.error(f"{self.log_prefix}IOError writing to locator log file {LOCATOR_STORAGE_FILE_PATH}: {e}")
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Unexpected error writing to locator log file {LOCATOR_STORAGE_FILE_PATH}: {e}", exc_info=True)

    # ... (rest of your BaseFiller class, including analyze_large_html_with_ai, find_element, etc.)
    # Ensure find_element, type_text, click_element, select_dropdown_option, upload_file, navigate methods exist
    # (These are assumed to be part of your BaseFiller from the context provided)

    @abstractmethod
    def fill_basic_info(self) -> bool:
        pass

    @abstractmethod
    def upload_documents(self) -> bool:
        pass

    @abstractmethod
    def answer_custom_questions(self) -> bool:
        pass

    @abstractmethod
    def review_and_submit(self) -> bool:
        pass
    
    @abstractmethod
    def navigate_to_start(self) -> bool:
        pass

    @abstractmethod
    def apply(self) -> str:
        pass

    def _get_safe_profile_json_for_prompt(self) -> str:
        # Placeholder: Implement or ensure this method exists and works.
        # self.logger.debug(f"{self.log_prefix}BaseFiller: Using default _get_safe_profile_json_for_prompt.")
        try:
            return json.dumps(self.user_profile)[:self.MAX_HTML_CHUNK_SIZE] # Basic serialization
        except TypeError:
            # Fallback for complex objects, ideally use a more robust serializer
            return json.dumps(str(self.user_profile))[:self.MAX_HTML_CHUNK_SIZE]


    def _get_safe_job_json_for_prompt(self) -> str:
        # Placeholder: Implement or ensure this method exists and works.
        # self.logger.debug(f"{self.log_prefix}BaseFiller: Using default _get_safe_job_json_for_prompt.")
        try:
            return json.dumps(self.job_data)[:self.MAX_HTML_CHUNK_SIZE] # Basic serialization
        except TypeError:
            return json.dumps(str(self.job_data))[:self.MAX_HTML_CHUNK_SIZE]


    def analyze_large_html_with_ai(self, html_content: str, prompt_template: str, cache_key: str,
                                   max_chunk_size: Optional[int] = None,
                                   context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyzes large HTML content by chunking it and processing with an LLM.
        Includes caching, retries, and structured JSON output expectation.
        """
        if not self.llm:
            self.logger.error(f"{self.log_prefix}LLM client not available for AI analysis.")
            return {"error": "LLM client not available."}

        if cache_key in self._ai_cache:
            cached_item = self._ai_cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.CACHE_EXPIRY_SECONDS:
                self.logger.info(f"{self.log_prefix}Using cached AI analysis for '{cache_key}'.")
                return cached_item['data']
            else:
                self.logger.info(f"{self.log_prefix}Cache expired for '{cache_key}'. Re-analyzing.")
                del self._ai_cache[cache_key] # Remove expired entry

        max_chunk_size = max_chunk_size or self.MAX_HTML_CHUNK_SIZE
        
        profile_json = self._get_safe_profile_json_for_prompt()
        job_json = self._get_safe_job_json_for_prompt()

        # Add profile and job to the context_data if not already overridden by caller
        final_context_data = {
            "profile": profile_json,
            "job": job_json,
            **(context_data or {}) 
        }

        chunks = [html_content[i:i + max_chunk_size] for i in range(0, len(html_content), max_chunk_size)]
        aggregated_results = {"fields": [], "questions": [], "summary": "Initial chunk."} # Ensure keys exist
        
        final_parsed_response = {}

        for i, chunk in enumerate(chunks):
            attempt = 0
            success = False
            current_summary = aggregated_results.get("summary", f"Summary from previous {i} chunks.")
            
            # Prepare prompt with all available context
            prompt_fill_data = {
                "chunk": chunk,
                "summary": current_summary, # Summary of processing so far
                "chunk_num": i + 1,
                "total_chunks": len(chunks),
                **final_context_data # Includes profile, job, and any other context
            }
            
            # Ensure all placeholders in prompt_template are present in prompt_fill_data
            try:
                current_prompt = prompt_template.format(**prompt_fill_data)
            except KeyError as e:
                self.logger.error(f"{self.log_prefix}Missing key for prompt template: {e}. Available keys: {prompt_fill_data.keys()}")
                return {"error": f"Prompt template formatting error, missing key: {e}"}


            while attempt < self.MAX_AI_RETRIES and not success:
                try:
                    self.logger.info(f"{self.log_prefix}Sending chunk {i+1}/{len(chunks)} to AI for '{cache_key}'. Size: {len(chunk)} chars.")
                    ai_response = self.llm.invoke(current_prompt) # Ensure this matches your LLM client's method
                    
                    # Extract content, assuming response object has a 'content' attribute or similar
                    ai_response_content = getattr(ai_response, 'content', ai_response if isinstance(ai_response, str) else '')
                    
                    # Attempt to find JSON within ```json ``` markers
                    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", ai_response_content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1).strip()
                        try:
                            parsed_chunk_response = json.loads(json_str)
                            # Merge results (example for "fields" and "questions")
                            if "fields" in parsed_chunk_response and isinstance(parsed_chunk_response["fields"], list):
                                aggregated_results["fields"].extend(parsed_chunk_response["fields"])
                            if "questions" in parsed_chunk_response and isinstance(parsed_chunk_response["questions"], list):
                                aggregated_results["questions"].extend(parsed_chunk_response["questions"])
                            
                            # Update summary from the current chunk's analysis
                            aggregated_results["summary"] = parsed_chunk_response.get("summary", current_summary)
                            
                            # Store the last valid complete JSON response structure
                            final_parsed_response = parsed_chunk_response 
                            
                            success = True
                            self.logger.info(f"{self.log_prefix}Successfully processed AI response for chunk {i+1}/{len(chunks)}.")
                        except json.JSONDecodeError as e_json:
                            self.logger.warning(f"{self.log_prefix}AI response JSON parsing failed for chunk {i+1} (attempt {attempt+1}): {e_json}. Response snippet: {json_str[:200]}...")
                            if attempt + 1 >= self.MAX_AI_RETRIES:
                                self.logger.error(f"{self.log_prefix}Max retries reached for chunk {i+1}. Failed to parse JSON.")
                                return {"error": f"AI JSON parsing error after max retries for chunk {i+1}: {e_json}", "raw_response": json_str}
                    else:
                        self.logger.warning(f"{self.log_prefix}No JSON block found in AI response for chunk {i+1} (attempt {attempt+1}). Response: {ai_response_content[:200]}...")
                        if attempt + 1 >= self.MAX_AI_RETRIES:
                            self.logger.error(f"{self.log_prefix}Max retries reached for chunk {i+1}. No JSON block found.")
                            return {"error": f"AI response format error (no JSON block) after max retries for chunk {i+1}", "raw_response": ai_response_content}

                except Exception as e_llm:
                    self.logger.error(f"{self.log_prefix}LLM invocation failed for chunk {i+1} (attempt {attempt+1}): {e_llm}", exc_info=True)
                    if attempt + 1 >= self.MAX_AI_RETRIES:
                        self.logger.error(f"{self.log_prefix}Max retries reached for LLM invocation on chunk {i+1}.")
                        return {"error": f"LLM error after max retries for chunk {i+1}: {e_llm}"}
                
                if not success:
                    attempt += 1
                    if attempt < self.MAX_AI_RETRIES:
                        self.logger.info(f"{self.log_prefix}Retrying AI analysis for chunk {i+1} in {self.AI_RETRY_DELAY}s...")
                        time.sleep(self.AI_RETRY_DELAY)
            
            if not success: # Should not happen if error returns are proper
                return {"error": f"Failed to process chunk {i+1} after all retries."}

        # After processing all chunks, the 'aggregated_results' should contain the combined data.
        # Or, if the AI is designed to return the full structure in the last chunk based on summary:
        # Use final_parsed_response which holds the JSON from the last successful chunk.
        # For this implementation, let's assume aggregated_results is what we want.
        # If the prompt asks the AI to consolidate, then the last chunk's response might be more appropriate.
        # Based on typical chunked summarization, aggregated_results is more robust if fields are additive.
        # If the AI's role is to produce ONE final JSON by the end, use `final_parsed_response`.
        # Given the prompt examples which seem to have `fields` and `questions` lists, aggregation is suitable.

        self._ai_cache[cache_key] = {'timestamp': time.time(), 'data': aggregated_results}
        # Manage cache size (optional, simple LRU-like behavior by removing oldest)
        while len(self._ai_cache) > 10: # Example cache size limit
            self._ai_cache.popitem(last=False)
            
        self.logger.info(f"{self.log_prefix}Completed AI analysis for '{cache_key}'.")
        return aggregated_results

    def find_element(self, locator: Tuple[str, str], wait_time: int = 10, fatal: bool = True,
                     element_name: Optional[str] = None) -> Optional[WebElement]:
        """Finds a web element with explicit wait, logging, and error handling."""
        name_for_log = element_name or f"element by {locator[0]}='{locator[1]}'"
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located(locator)
            )
            # self.logger.debug(f"{self.log_prefix}Found {name_for_log}.")
            return element
        except TimeoutException:
            if fatal:
                self.logger.error(f"{self.log_prefix}Timeout: {name_for_log} not found within {wait_time}s.")
                raise ApplicationError(f"{name_for_log} not found.")
            self.logger.warning(f"{self.log_prefix}Warning: {name_for_log} not found within {wait_time}s (non-fatal).")
            return None
        except Exception as e:
            if fatal:
                self.logger.error(f"{self.log_prefix}Error finding {name_for_log}: {e}", exc_info=True)
                raise ApplicationError(f"Error finding {name_for_log}: {e}")
            self.logger.warning(f"{self.log_prefix}Warning: Error finding {name_for_log} (non-fatal): {e}")
            return None
            
    def click_element(self, locator: Union[Tuple[str, str], WebElement], wait_time: int = 10,
                      desc: Optional[str] = None, fatal: bool = True, scroll_into_view: bool = True) -> bool:
        """Clicks an element with wait, error handling, and common interaction fixes."""
        element_desc = desc or (f"element by {locator[0]}='{locator[1]}'" if isinstance(locator, tuple) else "provided element")
        try:
            if isinstance(locator, tuple):
                web_element = WebDriverWait(self.driver, wait_time).until(
                    EC.element_to_be_clickable(locator)
                )
            elif isinstance(locator, WebElement):
                web_element = locator # Assume it's already interactable if passed directly
            else:
                self.logger.error(f"{self.log_prefix}Invalid locator type for click: {locator}")
                if fatal: raise ApplicationError("Invalid locator for click.")
                return False

            if scroll_into_view:
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", web_element)
                    time.sleep(0.3) # Short pause for scroll to complete
                except Exception as e_scroll:
                    self.logger.warning(f"{self.log_prefix}Could not scroll {element_desc} into view: {e_scroll}")
            
            web_element.click()
            # self.logger.info(f"{self.log_prefix}Clicked {element_desc}.")
            return True
        except (ElementClickInterceptedException, ElementNotInteractableException) as e_interact:
            self.logger.warning(f"{self.log_prefix}Standard click failed for {element_desc}: {e_interact}. Trying JavaScript click.")
            try:
                if not isinstance(locator, WebElement): # Re-fetch if locator was a tuple
                     web_element = self.find_element(locator, wait_time=3, fatal=False, element_name=element_desc) # type: ignore
                if web_element:
                    self.driver.execute_script("arguments[0].click();", web_element)
                    # self.logger.info(f"{self.log_prefix}Clicked {element_desc} using JavaScript.")
                    return True
                else:
                    raise e_interact # Could not re-find element
            except Exception as e_js:
                self.logger.error(f"{self.log_prefix}JavaScript click also failed for {element_desc}: {e_js}")
                if fatal: raise ApplicationError(f"Failed to click {element_desc}: {e_js}")
                return False
        except TimeoutException:
            msg = f"Timeout: {element_desc} not clickable within {wait_time}s."
            if fatal: self.logger.error(f"{self.log_prefix}{msg}"); raise ApplicationError(msg)
            self.logger.warning(f"{self.log_prefix}{msg} (non-fatal)")
            return False
        except Exception as e:
            msg = f"Error clicking {element_desc}: {e}"
            if fatal: self.logger.error(f"{self.log_prefix}{msg}", exc_info=True); raise ApplicationError(msg)
            self.logger.warning(f"{self.log_prefix}{msg} (non-fatal)", exc_info=True)
            return False

    def type_text(self, locator: Tuple[str, str], text: str, desc: Optional[str] = None,
                  wait_time: int = 10, clear_first: bool = True, fatal: bool = True,
                  click_before_type: bool = True) -> bool:
        """Types text into an element with wait, clear, logging, and error handling."""
        element_desc = desc or f"input field by {locator[0]}='{locator[1]}'"
        try:
            element = self.find_element(locator, wait_time=wait_time, fatal=False, element_name=element_desc)
            if not element:
                if fatal: raise ApplicationError(f"{element_desc} not found for typing.")
                return False

            if click_before_type: # Often helps focus the element
                self.driver.execute_script("arguments[0].click();", element) # JS click to ensure focus
                time.sleep(0.2)

            if clear_first:
                element.send_keys(Keys.CONTROL + "a" if sys.platform == "darwin" else Keys.CONTROL + "a") # Select all
                element.send_keys(Keys.DELETE)
                time.sleep(0.1) # Allow clear to process
                # Alternative clear: element.clear() - sometimes less reliable

            element.send_keys(text)
            # self.logger.info(f"{self.log_prefix}Typed '{text[:30]}...' into {element_desc}.")
            return True
        except Exception as e:
            msg = f"Error typing into {element_desc}: {e}"
            if fatal: self.logger.error(f"{self.log_prefix}{msg}", exc_info=True); raise ApplicationError(msg)
            self.logger.warning(f"{self.log_prefix}{msg} (non-fatal)", exc_info=True)
            return False

    def select_dropdown_option(self, locator: Tuple[str, str], option_text: Optional[str] = None,
                               option_value: Optional[str] = None, desc: Optional[str] = None,
                               wait_time: int = 10, fatal: bool = True) -> bool:
        """Selects an option in a dropdown by visible text or value."""
        element_desc = desc or f"dropdown by {locator[0]}='{locator[1]}'"
        try:
            select_element = self.find_element(locator, wait_time=wait_time, fatal=False, element_name=element_desc)
            if not select_element:
                if fatal: raise ApplicationError(f"{element_desc} (select element) not found.")
                return False

            select = Select(select_element)
            if option_text is not None:
                select.select_by_visible_text(option_text)
                # self.logger.info(f"{self.log_prefix}Selected '{option_text}' in {element_desc}.")
            elif option_value is not None:
                select.select_by_value(option_value)
                # self.logger.info(f"{self.log_prefix}Selected option with value '{option_value}' in {element_desc}.")
            else:
                self.logger.warning(f"{self.log_prefix}No option text or value provided for {element_desc}.")
                if fatal: raise ApplicationError(f"No option specified for {element_desc}")
                return False
            return True
        except NoSuchElementException: # For Select specific errors like option not found
            msg = f"Option '{option_text or option_value}' not found in {element_desc}."
            if fatal: self.logger.error(f"{self.log_prefix}{msg}"); raise ApplicationError(msg)
            self.logger.warning(f"{self.log_prefix}{msg} (non-fatal)")
            return False
        except Exception as e:
            msg = f"Error selecting option in {element_desc}: {e}"
            if fatal: self.logger.error(f"{self.log_prefix}{msg}", exc_info=True); raise ApplicationError(msg)
            self.logger.warning(f"{self.log_prefix}{msg} (non-fatal)", exc_info=True)
            return False
            
    def upload_file(self, locator: Tuple[str, str], file_path: str, desc: Optional[str] = None,
                    wait_time: int = 10, fatal: bool = True) -> bool:
        """Uploads a file to a file input element."""
        element_desc = desc or f"file input by {locator[0]}='{locator[1]}'"
        
        resolved_file_path = str(Path(file_path).resolve())
        if not Path(resolved_file_path).exists():
            self.logger.error(f"{self.log_prefix}File not found at path: {resolved_file_path} for {element_desc}.")
            if fatal: raise ApplicationError(f"File not found for upload: {resolved_file_path}")
            return False

        try:
            # File inputs are often not visible or interactable directly for EC.element_to_be_clickable
            # EC.presence_of_element_located is usually sufficient for send_keys to work
            file_input = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located(locator)
            )
            file_input.send_keys(resolved_file_path)
            # self.logger.info(f"{self.log_prefix}Uploaded file '{Path(resolved_file_path).name}' to {element_desc}.")
            time.sleep(1) # Give a moment for the upload to register on the UI
            return True
        except TimeoutException:
            msg = f"Timeout: {element_desc} not found for file upload within {wait_time}s."
            if fatal: self.logger.error(f"{self.log_prefix}{msg}"); raise ApplicationError(msg)
            self.logger.warning(f"{self.log_prefix}{msg} (non-fatal)")
            return False
        except Exception as e:
            msg = f"Error uploading file to {element_desc}: {e}"
            if fatal: self.logger.error(f"{self.log_prefix}{msg}", exc_info=True); raise ApplicationError(msg)
            self.logger.warning(f"{self.log_prefix}{msg} (non-fatal)", exc_info=True)
            return False

    def navigate(self, url: str) -> bool:
        """Navigates to a URL with error handling."""
        try:
            self.driver.get(url)
            self.logger.info(f"{self.log_prefix}Navigated to {url}.")
            WebDriverWait(self.driver, 15).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            return True
        except WebDriverException as e:
            self.logger.error(f"{self.log_prefix}WebDriverException during navigation to {url}: {e}", exc_info=True)
            raise ApplicationError(f"Failed to navigate to {url}: {e}")
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Unexpected error navigating to {url}: {e}", exc_info=True)
            raise ApplicationError(f"Unexpected error navigating to {url}: {e}")

    def ai_generate_field_value(self, field_label: str, field_type: str = "text", is_required: bool = False) -> Optional[str]:
        """Uses AI to generate a suitable value for a form field."""
        self.logger.info(f"{self.log_prefix}Attempting AI generation for field: '{field_label}' (Type: {field_type}, Required: {is_required})")
        if not self.llm:
            self.logger.warning(f"{self.log_prefix}LLM client not available, cannot generate value for '{field_label}'.")
            return "Not Available (LLM Error)" if is_required else None

        try:
            profile_summary = f"Relevant User Profile Info: Name - {self.user_profile.get('first_name', '')} {self.user_profile.get('last_name', '')}, Email - {self.user_profile.get('email', '')}, Phone - {self.user_profile.get('phone', '')}. Skills: {', '.join(self.user_profile.get('skills', [])[:3])}."
            job_summary = f"Applying for: {self.job_data.get('title', 'N/A')} at {self.job_data.get('company', 'N/A')}."

            prompt = (
                f"You are an assistant helping fill out a job application. "
                f"Generate an appropriate and concise value for the following form field:\n"
                f"Field Label: \"{field_label}\"\n"
                f"Field Type: \"{field_type}\"\n"
                f"Is Required: {is_required}\n"
                f"{job_summary}\n"
                f"{profile_summary}\n"
                f"Context: This is part of an automated job application process. "
                f"If the field is about salary, say 'Based on profile and market rates'. "
                f"If it's a generic 'cover letter' or 'additional information' and not strictly required, suggest a brief positive closing or 'Refer to resume'. "
                f"If it's a question you cannot answer from the provided profile, state 'Information not available in profile.' "
                f"Only provide the value, no explanations or labels. If not applicable and not required, output 'N/A'."
                f"Value:"
            )
            
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
                f"Question: {question_text}\\nAnswer:"
            )
            response = self.llm.invoke(prompt)
            answer = getattr(response, 'content', '')
            self.logger.info(f"{self.log_prefix}Generated AI answer snippet: {answer[:60]}...")
            return answer or "Not Applicable."
        except Exception as e:
            self.logger.error(f"{self.log_prefix}LLM invocation failed for question: {e}")
            return "Error generating answer."


# Placeholder for re (regular expression) import, if not already present at the top of base_filler.py
import re