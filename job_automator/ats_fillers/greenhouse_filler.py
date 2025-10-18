# job_automator/ats_fillers/greenhouse_filler.py

import logging
import time
import json # Make sure json is imported
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any # Added Any
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from .base_filler import BaseFiller, ApplicationError # Ensure BaseFiller is correctly imported
import config # Assuming config is in the accessible path
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, ElementClickInterceptedException,
    WebDriverException, NoSuchFrameException
)
# Add these MongoDB imports (if using MongoDB)
from datetime import datetime, date
# import json # Already imported above
from bson import ObjectId
# from typing import Any # Already imported above

try:
    from bson import ObjectId
    HAS_MONGO = True
except ImportError:
    HAS_MONGO = False
    ObjectId = type('ObjectId', (), {})


class GreenhouseFiller(BaseFiller):
    """Complete Greenhouse implementation with chunked AI processing"""
    
    logger = logging.getLogger(__name__) # This will use GreenhouseFiller as the logger name

    DEFAULT_FILE_INPUT_LOCATOR = (By.XPATH, "//input[@type='file' and contains(@accept, 'pdf')]")
    
    # Base locators
    LOCATORS = {
        "application_form": (By.ID, "application_form"),
        "confirmation_message": (By.XPATH, "//*[contains(., 'Application Submitted')]"),
    }

    # Field type handlers
    FIELD_HANDLERS = {
        "text": "_fill_text_field",
        "select": "_fill_select_field",
        "radio": "_fill_radio_field",
        "checkbox": "_fill_checkbox_field",
        "file": "_fill_file_field"
    }

    def __init__(self, driver, job_data, user_profile, document_paths, credentials=None):
        super().__init__(driver, job_data, user_profile, document_paths, credentials)
        self._form_analysis = None
        # Update log_prefix for this specific filler instance
        self.log_prefix = f"[GreenhouseFiller - JobID: {self._validate_job_id(self.job_data.get('job_id'))}] "


    def _validate_job_id(self, job_id) -> str:
        """Handle various ID formats including MongoDB ObjectId"""
        try:
            if HAS_MONGO and isinstance(job_id, ObjectId):
                return str(job_id)
            return str(job_id) if job_id else "unknown_id"
        except Exception:
            return "unknown_id" # Fallback for any error during validation
        
    def _safe_json_dumps(self, data: Any, max_length: int = 2000) -> str:
        """Safely convert data to JSON with length limit"""
        try:
            return json.dumps(self._safe_serialize(data))[:max_length]
        except Exception as e:
            self.logger.warning(f"{self.log_prefix}JSON serialization warning: {str(e)}")
            return "{}"

    def fill_basic_info(self) -> bool:
        """AI-powered basic info filling with chunked processing"""
        try:
            form = self.find_element(self.LOCATORS["application_form"], fatal=True, element_name="Application Form")
            if not form: return False # Should be handled by fatal=True in find_element
            form_html = form.get_attribute('outerHTML')

            prompt = """Analyze this form chunk and identify fields to fill. Focus on:
- Personal info (name, email, phone)
- Professional info (LinkedIn, GitHub)
- Location details

For each field:
1. Provide exact locator as a list ["type", "value"] (e.g., ["id", "full_name"] or ["xpath", "//input[@name='firstName']"])
2. Mark if required (true/false)
3. Suggest value from profile or generate if missing
4. For sensitive fields, recommend 'prefer not to say'

Current Profile:
{profile}

Job Details:
{job}

HTML Chunk:
{chunk}

Summary of previous processing: {summary}
Chunk {chunk_num} of {total_chunks}

IMPORTANT: Your response must be VALID JSON between ```json ``` markers.
Do NOT include any other text outside these markers.

Example response:
```json
{{
    "fields": [
        {{
            "label": "Full Name",
            "type": "text",
            "required": true,
            "locator": ["id", "full_name"],
            "value": "John Doe",
            "source": "profile"
        }}
    ],
    "summary": "Processed personal info fields"
}}
```"""
            
            validated_job_id = self._validate_job_id(self.job_data.get('job_id'))
            analysis = self.analyze_large_html_with_ai(
                form_html,
                prompt,
                cache_key=f"basic_info_{validated_job_id}"
            )
            self._form_analysis = analysis

            if analysis and "fields" in analysis:
                for field_data in analysis.get("fields", []):
                    if "locator" in field_data and field_data["locator"]:
                        # Ensure field_data["locator"] is a list, e.g. ["id", "value"]
                        self._log_ai_locator(
                            label=field_data.get("label", "Unknown Basic Info Field"),
                            locator=field_data["locator"], # Expected format: ["type", "value"]
                            context="Greenhouse Basic Info Form",
                            ats_platform="Greenhouse",
                            job_id_str=validated_job_id
                        )
            
            return self._execute_field_instructions(analysis.get("fields", []))
        except ApplicationError as e: # Catch specific application errors
            self.logger.error(f"{self.log_prefix}Basic info filling failed (ApplicationError): {e.message}", exc_info=False)
            return False
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Basic info filling failed (Exception): {str(e)}", exc_info=True)
            return False
        
    def upload_documents(self) -> bool:
        """Handle document uploads with AI assistance if needed"""
        try:
            # Resume (required)
            resume_path = self.document_paths.get("resume")
            if not resume_path:
                self.logger.error(f"{self.log_prefix}No resume path provided.")
                raise ApplicationError("No resume path provided")
                
            if not self._upload_resume(resume_path):
                self.logger.warning(f"{self.log_prefix}Resume upload was not successful.")
                return False # Resume upload is critical
                
            # Cover letter (optional)
            cover_letter_path = self.document_paths.get("cover_letter")
            if cover_letter_path: # Check if path exists and is not empty
                self.logger.info(f"{self.log_prefix}Attempting to upload cover letter.")
                if not self._upload_cover_letter(cover_letter_path): # Log if optional upload fails
                    self.logger.warning(f"{self.log_prefix}Optional cover letter upload failed or no field found.")
            else:
                self.logger.info(f"{self.log_prefix}No cover letter path provided, skipping upload.")
                
            return True
        except ApplicationError as e:
            self.logger.error(f"{self.log_prefix}Document upload failed (ApplicationError): {e.message}", exc_info=False)
            return False
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Document upload failed (Exception): {str(e)}", exc_info=True)
            return False

    def answer_custom_questions(self) -> bool:
        """AI-powered custom question answering"""
        try:
            # First handle standard EEO questions
            if not self._handle_eeo_questions(): # Check return value
                 self.logger.warning(f"{self.log_prefix}EEO question handling encountered issues or no questions found.")
            
            # Then analyze custom questions with AI
            # Using a more generic class that might contain custom questions
            questions_section_locator = (By.XPATH, "//*[contains(@id, 'custom_fields')] | //*[contains(@class, 'custom-questions')] | //form[@id='application_form']//div[contains(@class,'field') or contains(@class,'question')]")
            
            questions_section = self.find_element(
                questions_section_locator,
                wait_time=5, # Short wait, might not always exist
                fatal=False, # Don't fail if no specific custom questions section is obvious
                element_name="Custom Questions Section"
            )
            
            # If a specific section isn't found, use the whole form for question analysis
            # This is a fallback, assuming custom questions might be interspersed
            if not questions_section:
                self.logger.info(f"{self.log_prefix}No distinct custom questions section found by specific locator, will analyze whole form for custom questions.")
                form_element = self.find_element(self.LOCATORS["application_form"], fatal=False, element_name="Application Form for Custom Questions")
                if form_element:
                    questions_section = form_element
                else:
                    self.logger.warning(f"{self.log_prefix}Application form not found for custom question analysis. Skipping AI custom questions.")
                    return True # No section to analyze means no custom questions to fail on here

            return self._handle_custom_questions_with_ai(questions_section)

        except ApplicationError as e:
            self.logger.error(f"{self.log_prefix}Custom questions step failed (ApplicationError): {e.message}", exc_info=False)
            return False
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Custom questions step failed (Exception): {str(e)}", exc_info=True)
            return False

    def review_and_submit(self) -> bool:
        """Final review and submission"""
        try:
            # Scroll through form to trigger any validation
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5) # Brief pause for scroll
            self.driver.execute_script("window.scrollTo(0, 0);") # Scroll back to top
            time.sleep(0.5) # Brief pause

            # More robust submit button locator
            submit_button_locators = [
                (By.XPATH, "//button[@type='submit' and (contains(., 'Submit Application') or contains(., 'Submit'))]"),
                (By.XPATH, "//input[@type='submit' and (contains(@value, 'Submit Application') or contains(@value, 'Submit'))]"),
                (By.ID, "submit_button"), # Common ID
            ]
            
            submit_button_element = None
            for i, locator in enumerate(submit_button_locators):
                self.logger.info(f"{self.log_prefix}Trying submit button locator strategy {i+1}: {locator}")
                submit_button_element = self.find_element(locator, wait_time=5, fatal=False, element_name=f"Submit Button (Strategy {i+1})")
                if submit_button_element:
                    break
            
            if not submit_button_element:
                self.logger.error(f"{self.log_prefix}Submit button not found with any strategy.")
                raise ApplicationError("Submit button not found.")

            if not self.click_element(submit_button_element, desc="Submit Application Button", fatal=True):
                self.logger.error(f"{self.log_prefix}Failed to click submit button.")
                return False # click_element already raised if fatal=True
                
            # Verify submission
            time.sleep(config.TIMEOUTS.get("SUBMISSION_CONFIRMATION", 5)) # Use configured timeout
            
            # More robust confirmation message check
            confirmation_locators = [
                self.LOCATORS["confirmation_message"],
                (By.XPATH, "//*[contains(text(), 'Thank you for your application')]"),
                (By.XPATH, "//*[contains(text(), 'Application received')]"),
                (By.XPATH, "//*[contains(text(), 'Successfully submitted')]"),
                (By.XPATH, "//*[contains(text(), 'Your application has been submitted')]"),
            ]

            confirmed = False
            for i, locator in enumerate(confirmation_locators):
                self.logger.info(f"{self.log_prefix}Trying confirmation message locator strategy {i+1}: {locator}")
                if self.find_element(locator, wait_time=5, fatal=False, element_name=f"Confirmation Message (Strategy {i+1})"):
                    confirmed = True
                    self.logger.info(f"{self.log_prefix}Application submission confirmed with strategy {i+1}.")
                    break
            
            if not confirmed:
                 self.logger.warning(f"{self.log_prefix}No explicit confirmation message found. Assuming submission might have passed if no error.")
                 # Depending on strictness, you might return False here or rely on absence of prior errors.
                 # For now, let's be optimistic if no error occurred during click.
                 # However, if LOCATORS["confirmation_message"] is critical, this should be stricter.
                 # Re-evaluating: if the primary confirmation locator is defined, it should be found.
                 if self.find_element(self.LOCATORS["confirmation_message"], wait_time=1, fatal=False): # Quick recheck of primary
                     return True
                 self.logger.error(f"{self.log_prefix}Primary confirmation message '{self.LOCATORS['confirmation_message']}' not found after submission.")
                 return False


            return True
        except ApplicationError as e:
            self.logger.error(f"{self.log_prefix}Submission failed (ApplicationError): {e.message}", exc_info=False)
            return False
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Submission failed (Exception): {str(e)}", exc_info=True)
            return False

    # AI-powered implementation details
    def _execute_field_instructions(self, fields: List[Dict]) -> bool:
        """Execute field filling instructions from AI"""
        if not fields:
            self.logger.info(f"{self.log_prefix}No field instructions to execute.")
            return True # No fields means success in doing nothing.

        all_successful = True
        for field in fields:
            try:
                field_label = field.get("label", "Unknown field")
                field_type = field.get("type")
                
                handler_name = self.FIELD_HANDLERS.get(field_type)
                if not handler_name:
                    self.logger.warning(f"{self.log_prefix}No handler for field type: {field_type} (Label: {field_label})")
                    continue # Skip this field, don't mark as failure for the whole process unless critical
                    
                handler_method = getattr(self, handler_name, None)
                if not handler_method:
                    self.logger.error(f"{self.log_prefix}Handler method {handler_name} not found for type {field_type}.")
                    all_successful = False # This is a programming error
                    continue

                self.logger.info(f"{self.log_prefix}Processing field '{field_label}' (Type: {field_type})")
                if not handler_method(field): # Pass the whole field dict
                    self.logger.warning(f"{self.log_prefix}Failed to fill field: '{field_label}' (Type: {field_type}). Required: {field.get('required', False)}")
                    if field.get("required", False): # Only mark as overall failure if a required field fails
                        all_successful = False
            except Exception as e:
                self.logger.error(f"{self.log_prefix}Error processing field instruction for '{field.get('label', 'Unknown')}': {str(e)}", exc_info=True)
                if field.get("required", False):
                    all_successful = False # Critical error on a required field
        return all_successful
    
    def _safe_serialize(self, data: Any) -> Any:
        """Convert non-JSON-serializable objects to serializable formats."""
        if isinstance(data, ObjectId):
            # self.logger.debug(f"{self.log_prefix}GreenhouseFiller._safe_serialize: Converting ObjectId '{str(data)}' to string.")
            return str(data)
        elif isinstance(data, dict):
            return {k: self._safe_serialize(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._safe_serialize(v) for v in data]
        #elif hasattr(data, '__dict__'): # Be careful with this, can lead to large objects or recursion
        #    return self._safe_serialize(data.__dict__)
        elif isinstance(data, (datetime, date)):
            return data.isoformat() 
        try: # Attempt to stringify if unknown, but log it
            json.dumps(data) # Test if serializable
            return data
        except TypeError:
            # self.logger.debug(f"{self.log_prefix}_safe_serialize: Converting type {type(data)} to string representation.")
            return str(data) # Fallback to string representation

    # Override methods from BaseFiller
    def _get_safe_profile_json_for_prompt(self) -> str:
        # self.logger.debug(f"{self.log_prefix}GreenhouseFiller: Overriding _get_safe_profile_json_for_prompt. Using self._safe_json_dumps.")
        # self.logger.debug(f"{self.log_prefix}GreenhouseFiller: user_profile before _safe_json_dumps (first 200 chars): {str(self.user_profile)[:200]}")
        # Use a reasonable max length, e.g., from a config or a smaller portion of MAX_HTML_CHUNK_SIZE
        profile_max_len = getattr(config, "AI_PROMPT_PROFILE_MAX_LEN", 3000)
        serialized_profile_data = self._safe_json_dumps(self.user_profile, max_length=profile_max_len)
        # self.logger.debug(f"{self.log_prefix}GreenhouseFiller: user_profile after _safe_json_dumps (first 200 chars): {serialized_profile_data[:200]}")
        return serialized_profile_data

    def _get_safe_job_json_for_prompt(self) -> str:
        # self.logger.debug(f"{self.log_prefix}GreenhouseFiller: Overriding _get_safe_job_json_for_prompt. Using self._safe_json_dumps.")
        job_id_val = self.job_data.get('job_id')
        # if isinstance(job_id_val, ObjectId): 
        #     self.logger.info(f"{self.log_prefix}GreenhouseFiller: job_data contains ObjectId for job_id: {job_id_val}")
        # self.logger.debug(f"{self.log_prefix}GreenhouseFiller: job_data before _safe_json_dumps (first 200 chars): {str(self.job_data)[:200]}")
        job_max_len = getattr(config, "AI_PROMPT_JOB_MAX_LEN", 2000)
        serialized_job_data = self._safe_json_dumps(self.job_data, max_length=job_max_len) 
        # self.logger.debug(f"{self.log_prefix}GreenhouseFiller: job_data after _safe_json_dumps (first 200 chars): {serialized_job_data[:200]}")
        return serialized_job_data
    
    def _handle_eeo_questions(self) -> bool:
        """Standard EEO question handling by selecting 'decline' or 'prefer not to say'."""
        self.logger.info(f"{self.log_prefix}Handling EEO questions.")
        # More comprehensive list of phrases indicating decline/prefer not to say
        decline_phrases = [
            "decline to self-identify", "prefer not to say", "i don't wish to answer",
            "choose not to disclose", "do not wish to provide", "decline to answer"
        ]
        
        # Construct XPath to find elements containing any of the decline phrases,
        # specifically looking for clickable inputs (radio/checkbox) or options within selects.
        # This targets labels often associated with radio buttons or options.
        # It's crucial that these elements are interactable.

        base_xpath_label_contains = "//*[self::label or self::span or self::div][({conditions}) and not(ancestor::*[contains(@style,'display:none')]) and not(ancestor::*[contains(@hidden, 'true')])]"
        
        condition_parts = [f"contains(normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')), '{phrase}')" for phrase in decline_phrases]
        full_conditions = " or ".join(condition_parts)
        
        # XPath for clickable elements (input type radio/checkbox) whose associated label (or themselves if value attr) matches
        # This is complex because the actual clickable element might be an input, and the text in a sibling/parent label.
        # Strategy 1: Find inputs whose *value* attribute matches common decline values (e.g., for radio buttons)
        # Strategy 2: Find labels with decline text, then try to click associated input or the label itself.

        overall_success = True
        elements_clicked_count = 0

        # Try finding elements by common patterns (more targeted)
        # Common pattern: a radio button or checkbox input
        # Looking for an input that is a sibling or child of a label containing the text, or the label itself
        # This can be very specific to HTML structures.

        # A simpler, more direct approach: find elements (buttons, links, radio labels) containing the text directly
        generic_clickable_xpath = "//(button|a|label|span)[{conditions}] | //input[@type='radio' or @type='checkbox'][@value/following-sibling::label[{conditions}]]"
        
        # Prioritize more specific selectors for common EEO structures like radio groups
        eeo_sections_xpaths = [
            "//div[contains(@class, 'eeo')]", # Common class for EEO sections
            "//fieldset[.//legend[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'equal opportunity')]]", # Fieldset with EEO legend
            "//div[h3|h4|h5|legend[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'gender') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'race') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'ethnicity') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'veteran') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),'disability')]]"
        ]

        eeo_elements_found_in_sections = False
        for section_xpath in eeo_sections_xpaths:
            sections = self.driver.find_elements(By.XPATH, section_xpath)
            if not sections:
                continue
            
            self.logger.info(f"{self.log_prefix}Found potential EEO section(s) with XPath: {section_xpath}")
            for section in sections:
                for phrase in decline_phrases:
                    # Try to find clickable elements within this section
                    # 1. Inputs (radio/checkbox) where a *following or parent label* contains the phrase
                    #    This is tricky with generic XPath. Let's try finding labels first.
                    decline_labels_in_section = section.find_elements(By.XPATH, f".//label[contains(normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')), '{phrase.lower()}')]")
                    for label in decline_labels_in_section:
                        try:
                            # Try to click the label first, as it often triggers the associated input
                            if self.click_element(label, wait_time=1, desc=f"EEO Decline Label ('{phrase}')", fatal=False, scroll_into_view=True):
                                self.logger.info(f"{self.log_prefix}Clicked EEO decline option (label): '{phrase}'")
                                elements_clicked_count +=1
                                eeo_elements_found_in_sections = True
                                time.sleep(0.3) # Pause after click
                                continue # Move to next phrase or section
                            
                            # If label click fails or is not desired, try finding associated input
                            input_id = label.get_attribute("for")
                            if input_id:
                                associated_input = self.find_element((By.ID, input_id), wait_time=1, fatal=False)
                                if associated_input and self.click_element(associated_input, wait_time=1, desc=f"EEO Decline Input for '{phrase}'", fatal=False, scroll_into_view=True):
                                    self.logger.info(f"{self.log_prefix}Clicked EEO decline option (associated input): '{phrase}'")
                                    elements_clicked_count +=1
                                    eeo_elements_found_in_sections = True
                                    time.sleep(0.3)
                                    continue
                        except Exception as e_click:
                            self.logger.warning(f"{self.log_prefix}Minor issue clicking EEO element for phrase '{phrase}': {e_click}")
                    
                    # 2. Direct clickable elements (button, a) containing the phrase
                    decline_buttons_in_section = section.find_elements(By.XPATH, f".//(button|a)[contains(normalize-space(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')), '{phrase.lower()}')]")
                    for button_like in decline_buttons_in_section:
                        if self.click_element(button_like, wait_time=1, desc=f"EEO Decline Button/Link ('{phrase}')", fatal=False, scroll_into_view=True):
                            self.logger.info(f"{self.log_prefix}Clicked EEO decline option (button/link): '{phrase}'")
                            elements_clicked_count +=1
                            eeo_elements_found_in_sections = True
                            time.sleep(0.3)
                            break # Assuming one click per phrase type is enough for that section

        if elements_clicked_count > 0:
            self.logger.info(f"{self.log_prefix}Successfully clicked {elements_clicked_count} EEO 'decline/prefer not to say' options.")
            return True
        
        if not eeo_elements_found_in_sections:
             self.logger.info(f"{self.log_prefix}No specific EEO decline/prefer not to say options found or clicked in identified sections. This might be okay if questions are not present.")
        
        return overall_success # Returns true if no errors, even if no elements clicked (might be no EEO)

    def _handle_custom_questions_with_ai(self, section: WebElement) -> bool:
        """Analyze and answer custom questions with chunked AI processing"""
        if not section:
            self.logger.info(f"{self.log_prefix}No section provided for custom question analysis.")
            return True # No questions to answer here

        section_html = section.get_attribute('outerHTML')
        if not section_html or len(section_html) < 50: # Heuristic for empty/trivial section
            self.logger.info(f"{self.log_prefix}Custom questions section HTML is trivial or empty. Skipping AI analysis for it.")
            return True
            
        self.logger.info(f"{self.log_prefix}Analyzing custom questions section (HTML length: {len(section_html)}).")

        prompt = """Analyze these custom job application questions from the HTML chunk:
        
        Job Requirements (for context):
        {job}
        
        Applicant Profile (for context):
        {profile}
        
        Summary from previous chunks (if any):
        {summary}
        
        Current HTML Chunk of Questions ({chunk_num}/{total_chunks}):
        {chunk}
        
        For each distinct question found in this chunk:
        1. Identify the main question text/label.
        2. Determine the question type (e.g., "text", "textarea", "radio", "checkbox", "select").
        3. Provide an exact locator for the input field(s) or select element as a list ["type", "value"] (e.g., ["name", "question1"] or ["xpath", "//textarea[@id='q1']"]). For radio/checkbox groups, provide the locator for the specific option to select if inferable, otherwise the group.
        4. Based on the profile and job context, generate a concise, professional answer.
        5. If the question is sensitive (e.g., race, gender, disability) and an answer is not mandatory or can be "Prefer not to say", suggest that or an empty answer.
        6. If it's a radio/checkbox and you need to choose an option, the "answer" should be the value/text of the option to select, and the "locator" should point to that specific option's input element.

        Return a VALID JSON object between ```json ``` markers:
        ```json
        {{
            "questions": [
                {{
                    "text": "What is your salary expectation?",
                    "type": "text", // or "textarea"
                    "locator": ["xpath", "//input[@name='salary_expectation']"],
                    "answer": "Based on my experience and market rates for similar roles.",
                    "source": "generated",
                    "sensitive": false
                }},
                {{
                    "text": "Are you authorized to work in the US?",
                    "type": "radio", // Could be "select" or "checkbox"
                    "locator": ["xpath", "//input[@name='work_auth' and @value='Yes']"], // Locator for the 'Yes' option
                    "answer": "Yes", // This is the value that would be selected or typed
                    "source": "profile_or_generated",
                    "sensitive": false
                }}
            ],
            "summary": "Identified salary and work authorization questions. Needs more processing if other chunks."
        }}
        ```
        If no questions are found in this chunk, return an empty "questions" list.
        """
        
        validated_job_id = self._validate_job_id(self.job_data.get('job_id'))
        analysis = self.analyze_large_html_with_ai(
            section_html,
            prompt,
            cache_key=f"custom_questions_{validated_job_id}"
        )
        
        if analysis and "questions" in analysis:
            # Log identified locators before attempting to answer
            for question_data in analysis.get("questions", []):
                if "locator" in question_data and question_data["locator"]:
                    self._log_ai_locator(
                        label=question_data.get("text", "Unknown Custom Question"),
                        locator=question_data["locator"], # Expected ["type", "value"]
                        context="Greenhouse Custom Questions",
                        ats_platform="Greenhouse",
                        job_id_str=validated_job_id
                    )
            return self._answer_ai_questions(analysis.get("questions", [])) # Changed to _answer_ai_questions
        
        self.logger.info(f"{self.log_prefix}No custom questions identified by AI or analysis failed.")
        return True # If no questions, consider it a success for this step

    # Field type handlers
    def _fill_text_field(self, field: Dict) -> bool:
        """Handle text input fields based on AI instruction"""
        if not isinstance(field, dict) or "locator" not in field:
            self.logger.error(f"{self.log_prefix}Invalid field format for _fill_text_field: {field}")
            return False
            
        value_to_fill = self._get_field_value(field) # Gets value from field dict or generates if needed
        if value_to_fill is None and field.get("required", False):
            self.logger.warning(f"{self.log_prefix}No value obtained for required text field: {field.get('label', 'Unknown')}")
            return False # Cannot fill required field
        if value_to_fill is None: # Not required, and no value
             self.logger.info(f"{self.log_prefix}Skipping optional text field with no value: {field.get('label', 'Unknown')}")
             return True


        return self.type_text(
            tuple(field["locator"]), # Convert ["type", "value"] to ("type", "value")
            str(value_to_fill), # Ensure value is a string
            desc=field.get("label", "text field"),
            fatal=False # Individual field failures handled by _execute_field_instructions
        )

    def _fill_select_field(self, field: Dict) -> bool:
        """Handle dropdown/select fields based on AI instruction"""
        if not isinstance(field, dict) or "locator" not in field:
            self.logger.error(f"{self.log_prefix}Invalid field format for _fill_select_field: {field}")
            return False

        value_to_select = self._get_field_value(field)
        if value_to_select is None and field.get("required", False):
            self.logger.warning(f"{self.log_prefix}No value obtained for required select field: {field.get('label', 'Unknown')}")
            return False
        if value_to_select is None:
            self.logger.info(f"{self.log_prefix}Skipping optional select field with no value: {field.get('label', 'Unknown')}")
            return True
            
        return self.select_dropdown_option(
            tuple(field["locator"]),
            option_text=str(value_to_select), # AI should provide the visible text to select
            desc=field.get("label", "dropdown"),
            fatal=False
        )

    def _fill_radio_field(self, field: Dict) -> bool:
        """Handle radio button fields. AI should provide locator for the specific option."""
        if not isinstance(field, dict) or "locator" not in field:
            self.logger.error(f"{self.log_prefix}Invalid field format for _fill_radio_field: {field}")
            return False
        
        # For radio, the 'value' from AI might be the value of the option to select,
        # but the 'locator' should ideally point directly to the radio button input element.
        # If AI provides a locator to a specific radio option, we just click it.
        # If AI provides a group locator and a value, this handler would need to be more complex.
        # Assuming AI's locator in `field["locator"]` is for the specific radio button to click.
        
        self.logger.info(f"{self.log_prefix}Attempting to click radio button for '{field.get('label', field.get('value', 'Unknown radio option'))}' using locator {field['locator']}")
        return self.click_element(
            tuple(field["locator"]),
            desc=field.get("label", f"radio option {field.get('value', '')}"),
            fatal=False
        )

    def _fill_checkbox_field(self, field: Dict) -> bool:
        """Handle checkbox fields. AI provides locator for the specific checkbox."""
        if not isinstance(field, dict) or "locator" not in field:
            self.logger.error(f"{self.log_prefix}Invalid field format for _fill_checkbox_field: {field}")
            return False

        # Similar to radio, AI's locator should point to the checkbox input.
        # The 'value' might indicate whether it should be checked (e.g., "true", "yes") or a specific choice.
        # For simplicity, if a checkbox field is identified, we assume it should be checked.
        # More complex logic could be added based on field["value"].
        
        self.logger.info(f"{self.log_prefix}Attempting to click checkbox for '{field.get('label', 'Unknown checkbox')}' using locator {field['locator']}")
        return self.click_element(
            tuple(field["locator"]),
            desc=field.get("label", "checkbox"),
            fatal=False
        )

    def _fill_file_field(self, field: Dict) -> bool:
        """Handle file upload fields based on AI instruction."""
        if not isinstance(field, dict) or "locator" not in field:
            self.logger.error(f"{self.log_prefix}Invalid field format for _fill_file_field: {field}")
            return False

        # AI should specify 'document_type' (e.g., "resume", "cover_letter")
        # that maps to keys in self.document_paths
        doc_type = field.get("document_type")
        if not doc_type:
            self.logger.warning(f"{self.log_prefix}No 'document_type' specified for file field: {field.get('label', 'Unknown')}")
            return False # Cannot proceed without knowing which document

        file_path = self.document_paths.get(doc_type)
        if not file_path:
            self.logger.warning(f"{self.log_prefix}No file path found in document_paths for type '{doc_type}' (Label: {field.get('label')})")
            if field.get("required", False):
                return False # Required file not available
            return True # Optional file not available, skip

        self.logger.info(f"{self.log_prefix}Uploading file for '{field.get('label', doc_type)}' from path '{file_path}'")
        return self.upload_file(
            tuple(field["locator"]),
            file_path,
            desc=field.get("label", f"{doc_type} file input"),
            fatal=False
        )


    def _get_field_value(self, field: Dict) -> Optional[str]:
        """
        Determines the value for a field based on AI suggestion, profile, or generation.
        Handles 'prefer not to say' logic primarily by AI suggesting it or by AI not providing a value for optional sensitive fields.
        """
        field_label = field.get("label", "Unknown field")
        # self.logger.debug(f"{self.log_prefix}Getting value for field: '{field_label}' using data: {field}")

        # If AI explicitly suggests a value, use it.
        # This includes "Prefer not to say" if AI determined it.
        if "value" in field and field["value"] is not None:
            # self.logger.debug(f"{self.log_prefix}Using provided value for '{field_label}': '{str(field['value'])[:50]}'")
            return str(field["value"]) # Ensure it's a string

        # If field is marked as "source": "prefer_not" or similar by AI (hypothetical, not in current prompt)
        # This logic is mostly superseded by AI directly providing "Prefer not to say" as the value.
        # if field.get("source") == "prefer_not":
        #     self.logger.info(f"{self.log_prefix}AI indicated 'prefer_not' for '{field_label}'. Using 'Prefer not to say'.")
        #     return "Prefer not to say"

        # If the field is required and no value was provided by AI, try to generate one.
        if field.get("required", False):
            self.logger.info(f"{self.log_prefix}Required field '{field_label}' has no value from AI. Attempting to generate.")
            # The 'type' here is form field type (text, select), not document type
            generated_value = self.ai_generate_field_value(field_label, field.get("type", "text"), is_required=True)
            if generated_value:
                # self.logger.info(f"{self.log_prefix}Generated value for required field '{field_label}': '{generated_value[:50]}'")
                return generated_value
            else:
                self.logger.warning(f"{self.log_prefix}Could not generate value for required field '{field_label}'.")
                return None # Cannot satisfy required field

        # If not required and no value, implies optional and can be skipped.
        self.logger.info(f"{self.log_prefix}No value for optional field '{field_label}'. Will be skipped if handler allows.")
        return None


    def _select_prefer_not_option(self, field: Dict) -> bool:
        """
        Attempts to find and click a 'prefer not to say' or similar option
        related to the given field's locator. This is complex and unreliable
        without very specific HTML structure or AI identifying the exact 'decline' option's locator.
        It's generally better if AI's main field analysis directly provides "Prefer not to say"
        as the value for a text input, or provides the locator for the specific "decline" radio/select option.
        This method is kept for potential advanced scenarios but might be of limited use
        if AI field analysis is robust.
        """
        field_label = field.get("label", "Unknown Field")
        self.logger.info(f"{self.log_prefix}Attempting to find and select 'Prefer Not to Say' for field: {field_label}")

        # This requires knowledge of how "prefer not to say" options are structured relative to field["locator"]
        # It's highly dependent on the form.
        # Example: Try to find a sibling or child element near field["locator"]
        # This is a placeholder for more sophisticated logic if needed.
        # For now, this function is unlikely to be effective without more context.
        
        # Try generic phrases near the field, but this is a long shot.
        # The EEO handling is more comprehensive for dedicated EEO questions.
        # For general fields, it's hard to guess.
        decline_options_xpaths = [
            ".//*[self::option or self::label or self::span][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'prefer not to say')]",
            ".//*[self::option or self::label or self::span][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'decline to self-identify')]",
            # Add more generic xpaths if necessary, relative to the field's context if possible
        ]

        try:
            # Find the primary element of the field first to anchor the search
            primary_element = self.find_element(tuple(field["locator"]), wait_time=3, fatal=False, element_name=f"Primary element for {field_label}")
            if not primary_element:
                self.logger.warning(f"{self.log_prefix}Could not find primary element for '{field_label}' to search for 'prefer not to say' option.")
                return False

            # Search for decline options in the vicinity of the primary element
            # This looks for descendants. Might need preceding-sibling, following-sibling, parent etc.
            for i, decline_xpath_suffix in enumerate(decline_options_xpaths):
                try:
                    # Assuming primary_element is a Selenium WebElement
                    decline_element = primary_element.find_element(By.XPATH, decline_xpath_suffix) # Search relative to element
                    if decline_element:
                        if decline_element.tag_name == 'option':
                            # This would require getting the Select parent and selecting by this option's text/value
                            self.logger.info(f"{self.log_prefix}Found 'prefer not to say' option for '{field_label}', but it's an <option>. Complex selection needed.")
                            # TODO: Implement selection if it's an option within a select.
                            return False # Placeholder
                        elif self.click_element(decline_element, desc=f"Prefer not to say for {field_label} (Strategy {i})", wait_time=2, fatal=False):
                            self.logger.info(f"{self.log_prefix}Clicked 'prefer not to say' option for '{field_label}'.")
                            return True
                except NoSuchElementException:
                    continue # Try next XPath strategy
                except Exception as e_inner:
                    self.logger.warning(f"{self.log_prefix}Error while trying to click 'prefer not to say' for '{field_label}': {e_inner}")
                    
        except Exception as e_outer:
            self.logger.error(f"{self.log_prefix}Error finding primary element for '{field_label}' when searching for 'prefer not to say': {e_outer}")

        self.logger.info(f"{self.log_prefix}No 'prefer not to say' option explicitly clicked for field '{field_label}' via _select_prefer_not_option.")
        return False


    def _generate_field_value(self, field: Dict) -> Optional[str]:
        """Generate value for a field using AI (delegated to BaseFiller's method)."""
        field_label = field.get("label", "Unknown")
        field_type = field.get("type", "text")
        is_required = field.get("required", False)
        
        self.logger.info(f"{self.log_prefix}Generating AI value for field '{field_label}' (Type: {field_type}, Required: {is_required})")
        # Using the more generic method from BaseFiller, which now takes more context
        return self.ai_generate_field_value(field_label, field_type, is_required)


    # Document handling
    def _upload_resume(self, resume_path: str) -> bool:
        """Handle resume upload. Tries default, then common patterns, then AI-assisted locator."""
        self.logger.info(f"{self.log_prefix}Attempting to upload resume from: {resume_path}")
        
        # 1. Try the default locator defined in the class
        if self.find_element(self.DEFAULT_FILE_INPUT_LOCATOR, wait_time=2, fatal=False, element_name="Default Resume Input"):
            if self.upload_file(self.DEFAULT_FILE_INPUT_LOCATOR, resume_path, desc="Resume (Default Locator)"):
                self.logger.info(f"{self.log_prefix}Resume uploaded using default locator.")
                return True
            else:
                self.logger.warning(f"{self.log_prefix}Default resume input found, but upload failed. Trying other methods.")

        # 2. Try common explicit "Resume" upload locators
        # Variations in naming conventions for resume inputs
        common_resume_xpaths = [
            "//input[@type='file' and (@name='resume' or @id='resume' or contains(@aria-label, 'resume') or contains(@placeholder, 'resume'))]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload resume')]/preceding-sibling::input[@type='file']", # Button triggers hidden input
            "//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'resume')]/following-sibling::div//input[@type='file']", # Label then input nested
            "//div[contains(@class, 'resume-upload-trigger')]//input[@type='file']" # Custom component
        ]
        for i, xpath in enumerate(common_resume_xpaths):
            locator = (By.XPATH, xpath)
            # self.logger.debug(f"{self.log_prefix}Trying common resume locator strategy {i+1}: {locator}")
            if self.find_element(locator, wait_time=1, fatal=False, element_name=f"Resume Input (Common Strategy {i+1})"):
                if self.upload_file(locator, resume_path, desc=f"Resume (Common Strategy {i+1})"):
                    self.logger.info(f"{self.log_prefix}Resume uploaded using common strategy {i+1}.")
                    return True
                else:
                    self.logger.warning(f"{self.log_prefix}Common resume input (Strategy {i+1}) found, but upload failed.")
        
        # 3. Fallback to AI locator discovery
        self.logger.info(f"{self.log_prefix}Default and common resume locators failed or not found. Attempting AI locator discovery for resume.")
        form_element = self.find_element(self.LOCATORS["application_form"], element_name="Application Form for Resume AI analysis")
        if not form_element:
            self.logger.error(f"{self.log_prefix}Application form not found, cannot use AI to find resume field.")
            return False # Cannot proceed with AI if form is missing
            
        form_html = form_element.get_attribute('outerHTML')
        
        # Slightly more detailed prompt for file input
        prompt = """Analyze this HTML chunk of an application form. Identify the primary file input field for uploading a RESUME.
        Focus on <input type="file"> elements. Consider labels like "Resume", "CV", "Attach Resume".
        Prioritize inputs that accept PDF or DOCX files if specified.

        Current Profile:
        {profile}

        Job Details:
        {job}

        HTML Chunk:
        {chunk}

        Summary of previous processing: {summary}
        Chunk {chunk_num} of {total_chunks}

        Return a VALID JSON object between ```json ``` markers with the locator for the resume upload field:
        ```json
        {{
            "field_label": "Resume Upload", // The identified label of the field
            "locator": ["xpath", "//input[@id='resume_upload_input']"], // Precise locator as ["type", "value"]
            "file_types": ["pdf", "docx", "txt"], // Optional: detected accepted file types
            "summary": "Found resume input field."
        }}
        ```
        If no suitable resume input is found in this chunk, return null for "locator".
        """
        validated_job_id = self._validate_job_id(self.job_data.get('job_id'))
        ai_result = self.analyze_large_html_with_ai(
            form_html, 
            prompt,
            cache_key=f"resume_upload_locator_{validated_job_id}"
            )
        
        if ai_result and ai_result.get("locator"):
            ai_locator_list = ai_result["locator"] # Expected ["type", "value"]
            # Log this AI-identified locator
            self._log_ai_locator(
                label=ai_result.get("field_label", "Resume Upload Field (AI-identified)"),
                locator=ai_locator_list, # Pass the list directly
                context="Greenhouse Resume Upload (AI)",
                ats_platform="Greenhouse",
                job_id_str=validated_job_id
            )
            
            self.logger.info(f"{self.log_prefix}AI identified resume locator: {ai_locator_list}. Attempting upload.")
            if self.upload_file(
                tuple(ai_locator_list), # Convert list to tuple for upload_file
                resume_path,
                desc="Resume (AI-identified)"
            ):
                self.logger.info(f"{self.log_prefix}Resume uploaded successfully using AI-identified locator.")
                return True
            else:
                 self.logger.error(f"{self.log_prefix}AI identified resume locator {ai_locator_list}, but upload failed.")
                 # Fall through to raise ApplicationError as a last resort.
        
        self.logger.error(f"{self.log_prefix}Could not locate and successfully use resume upload field after all attempts.")
        raise ApplicationError("Could not locate or use resume upload field.") # Critical failure
    
    def navigate_to_start(self) -> bool:
        """Navigate to the application start URL"""
        app_url = self.job_data.get('application_url')
        if not app_url:
            self.logger.error(f"{self.log_prefix}No application URL provided in job data.")
            raise ApplicationError("No application URL provided in job data")
        self.logger.info(f"{self.log_prefix}Navigating to application start URL: {app_url}")
        return self.navigate(app_url)


    def _upload_cover_letter(self, cover_letter_path: str) -> bool:
        """Handle cover letter upload. Tries common patterns, then optionally AI."""
        self.logger.info(f"{self.log_prefix}Attempting to upload cover letter from: {cover_letter_path}")

        # Common cover letter input locators
        common_cl_xpaths = [
            "//input[@type='file' and (contains(@name, 'cover') or contains(@id, 'cover') or contains(@aria-label, 'cover') or contains(@placeholder, 'cover'))]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload cover letter')]/preceding-sibling::input[@type='file']",
            "//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cover letter')]/following-sibling::div//input[@type='file']",
        ]
        for i, xpath in enumerate(common_cl_xpaths):
            locator = (By.XPATH, xpath)
            # self.logger.debug(f"{self.log_prefix}Trying common cover letter locator strategy {i+1}: {locator}")
            cl_input_element = self.find_element(locator, wait_time=2, fatal=False, element_name=f"Cover Letter Input (Strategy {i+1})")
            if cl_input_element:
                if self.upload_file(locator, cover_letter_path, desc=f"Cover Letter (Strategy {i+1})"):
                    self.logger.info(f"{self.log_prefix}Cover letter uploaded using common strategy {i+1}.")
                    return True
                else: # Found element but upload failed
                    self.logger.warning(f"{self.log_prefix}Cover letter input (Strategy {i+1}) found, but upload failed. It might be optional.")
                    return False # Indicate failure to upload even if field found
        
        # Optional: AI-assisted cover letter field discovery (similar to resume, if desired)
        # For now, if common locators fail, we assume it's optional or not easily found.
        # Add AI discovery if cover letters are critical and often have varied locators.
        # Example AI call would mirror _upload_resume's AI part, with "cover letter" keywords.
        
        # If no specific "cover letter" input is found, check for generic additional document uploads
        generic_doc_xpaths = [
            "//input[@type='file' and (contains(@name, 'document') or contains(@id, 'additionalFile') or contains(@aria-label, 'additional document'))]",
            "//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'additional document')]/following-sibling::div//input[@type='file']"
        ]
        for i, xpath in enumerate(generic_doc_xpaths):
            locator = (By.XPATH, xpath)
            # self.logger.debug(f"{self.log_prefix}Trying generic document locator for cover letter (Strategy {i+1}): {locator}")
            if self.find_element(locator, wait_time=1, fatal=False, element_name=f"Generic Document Input for CL (Strategy {i+1})"):
                # Check if this field has already been used (e.g. by resume if locators were ambiguous)
                # This simple check might not be robust. A more stateful tracking of used inputs could be better.
                # For now, just try to upload.
                if self.upload_file(locator, cover_letter_path, desc=f"Cover Letter as Generic Document (Strategy {i+1})"):
                    self.logger.info(f"{self.log_prefix}Cover letter uploaded to a generic document field using strategy {i+1}.")
                    return True
                else:
                    self.logger.warning(f"{self.log_prefix}Generic document input for CL (Strategy {i+1}) found, but upload failed.")
                    return False

        self.logger.info(f"{self.log_prefix}No clear cover letter upload field found or upload failed. Skipping as it's often optional.")
        return False # Indicates cover letter was not uploaded.


    def _answer_ai_questions(self, questions_data: List[Dict]) -> bool: # Renamed from _answer_questions
        """Answers questions based on AI analysis from _handle_custom_questions_with_ai."""
        if not questions_data:
            self.logger.info(f"{self.log_prefix}No AI-identified custom questions to answer.")
            return True

        all_successful = True
        for q_data in questions_data:
            try:
                q_text = q_data.get("text", "Unknown question")
                q_type = q_data.get("type")
                q_locator_list = q_data.get("locator") # Expected ["type", "value"]
                q_answer = q_data.get("answer") # AI's suggested answer or option value

                if not q_locator_list:
                    self.logger.warning(f"{self.log_prefix}No locator provided for question: '{q_text}'. Skipping.")
                    # all_successful = False # Decide if this is a failure
                    continue
                
                q_locator_tuple = tuple(q_locator_list) # Convert to tuple for Selenium methods

                self.logger.info(f"{self.log_prefix}Answering question: '{q_text[:60]}...' (Type: {q_type}) with answer: '{str(q_answer)[:50]}...'")

                success_this_q = False
                if q_type in ["text", "textarea"]:
                    if q_answer is not None: # Allow empty string answer if AI suggests it
                        success_this_q = self.type_text(q_locator_tuple, str(q_answer), desc=q_text, fatal=False)
                    else: # No answer from AI for a text field
                        self.logger.warning(f"{self.log_prefix}No answer provided by AI for text question '{q_text}'. Skipping typing.")
                        success_this_q = True # Not necessarily a failure, could be optional
                
                elif q_type in ["radio", "checkbox"]:
                    # For radio/checkbox, the locator should ideally point to the specific option.
                    # The 'answer' from AI might be redundant if locator is specific, or it might be the 'value' to verify.
                    success_this_q = self.click_element(q_locator_tuple, desc=f"{q_text} (Option: {q_answer})", fatal=False)
                
                elif q_type == "select":
                    if q_answer:
                        success_this_q = self.select_dropdown_option(q_locator_tuple, option_text=str(q_answer), desc=q_text, fatal=False)
                    else:
                        self.logger.warning(f"{self.log_prefix}No answer (option text) provided by AI for select question '{q_text}'.")
                        success_this_q = True # Optional select might not need an answer
                else:
                    self.logger.warning(f"{self.log_prefix}Unsupported question type '{q_type}' for question: '{q_text}'")
                    # all_successful = False # Or just skip unsupported

                if not success_this_q:
                    self.logger.warning(f"{self.log_prefix}Failed to answer question: '{q_text}' (Type: {q_type}).")
                    # Decide if this specific failure makes all_successful false.
                    # For now, let's assume individual question failures are logged but don't stop the whole step unless critical.
                    # If a question is marked as "required" by AI, then failure should propagate.
                    # This "required" flag isn't in the current AI prompt for questions.
                    all_successful = False # Make it stricter: any failure in answering is a problem for the step.


            except Exception as e:
                self.logger.error(f"{self.log_prefix}Error answering AI question '{q_data.get('text', 'Unknown')}': {str(e)}", exc_info=True)
                all_successful = False
        
        return all_successful


    def _handle_manual_intervention(self, original_error: ApplicationError) -> str:
        """
        Pauses script execution when an error occurs, keeps the browser open,
        and waits for user input to determine the next step.
        """
        self.logger.info(f"‼️ APPLICATION ERROR: {original_error.message} (Status: {original_error.status})")
        self.logger.info("⏸️ PAUSING FOR MANUAL INTERVENTION. The browser window remains open.")
        self.logger.info("Please attempt to complete/fix the application manually in the browser.")
        self.logger.info("Once done, or if you close the window, please respond in THIS console window.")

        while True:
            try:
                # Check if the browser window is still accessible
                # A simple check is to see if there are any window handles.
                if not self.driver.window_handles:
                    self.logger.warning("Browser window appears to have been closed by the user.")
                    return config.JOB_STATUS_MANUAL_INTERVENTION_CLOSED_BY_USER

                user_choice = input(
                    "Enter your action -"
                    " 'submitted': if you successfully submitted the application |"
                    " 'closed': if you closed the browser or want to mark as user closed |"
                    " 'failed': if you tried but it still failed or want to use original error status "
                    "\nYour choice: "
                ).strip().lower()

                if user_choice == "submitted":
                    self.logger.info("User indicated: Application was manually submitted.")
                    # Optional: You could try to quickly verify if a confirmation message is visible
                    # if hasattr(self, 'check_for_confirmation_message') and self.check_for_confirmation_message(timeout=3):
                    #     self.logger.info("Confirmation message found on page after manual submission.")
                    #     return config.JOB_STATUS_APPLIED_SUCCESS # Or the manual submitted status
                    return config.JOB_STATUS_MANUAL_INTERVENTION_SUBMITTED
                elif user_choice == "closed":
                    self.logger.info("User indicated: Window closed or action aborted.")
                    # Important: Don't call self.driver.quit() here.
                    # The main script (automator_main.py) should manage the lifecycle of the driver.
                    # This status just signals the outcome of this specific job attempt.
                    return config.JOB_STATUS_MANUAL_INTERVENTION_CLOSED_BY_USER
                elif user_choice == "failed":
                    self.logger.info(f"User indicated: Manual attempt failed or use original error. Reverting to original status: {original_error.status}")
                    return original_error.status # Returns the original status like JOB_STATUS_APP_FAILED_ATS_STEP
                else:
                    self.logger.warning("Invalid choice. Please enter 'submitted', 'closed', or 'failed'.")

            except WebDriverException as e_wd:
                # This can happen if the window is closed while input() is waiting, then you try self.driver.window_handles
                self.logger.error(f"WebDriverException during manual intervention: {e_wd}")
                if "no such window" in str(e_wd).lower() or \
                   "target window already closed" in str(e_wd).lower() or \
                   (hasattr(self, 'driver') and not self.driver.window_handles): # Check again
                    self.logger.warning("Browser window was closed by the user (detected by WebDriverException).")
                    return config.JOB_STATUS_MANUAL_INTERVENTION_CLOSED_BY_USER
                self.logger.error("An unexpected WebDriver error occurred during intervention. Using original error status.")
                return original_error.status
            except KeyboardInterrupt:
                self.logger.warning("Manual intervention interrupted by user (Ctrl+C). Using original error status.")
                return original_error.status # Or a specific "interrupted" status
            except Exception as e_loop: # Catch-all for other unexpected issues in this loop
                self.logger.error(f"Unexpected error during manual intervention input loop: {e_loop}", exc_info=True)
                return original_error.status # Fallback to original error

    def apply(self) -> str:
        """Complete application flow with enhanced error handling and manual intervention."""
        try:
            self._ai_cache.clear()  # Clear previous analysis

            if not self.navigate_to_start():
                # Use a specific status from config if available, e.g. config.JOB_STATUS_APP_FAILED_NAVIGATION
                raise ApplicationError("Failed to navigate to application", config.JOB_STATUS_APP_FAILED_ATS)

            steps = [
                ("Basic info", self.fill_basic_info),
                ("Documents", self.upload_documents),
                ("Questions", self.answer_custom_questions),
                ("Submission", self.review_and_submit)
            ]

            for step_name, step_func in steps:
                if not step_func():
                    # Use the status for step failure (ensure it's defined in config.py)
                    raise ApplicationError(f"{step_name} step failed", config.JOB_STATUS_APP_FAILED_ATS_STEP)

            # If all steps complete, it's a success.
            # The review_and_submit step should ideally confirm submission.
            # If it doesn't raise an error, we assume it's successful here.
            return config.JOB_STATUS_APPLIED_SUCCESS

        except ApplicationError as e:
            # HERE IS THE KEY CHANGE: Call the intervention handler
            self.logger.error(f"Caught ApplicationError: {e.message}. Initiating manual intervention.")
            return self._handle_manual_intervention(e)
        except Exception as e_unexpected: # Catch other unexpected errors
            self.logger.critical(f"Unexpected critical error during application process: {str(e_unexpected)}", exc_info=True)
            # Create an ApplicationError to pass to the handler, using the appropriate status from config
            app_error = ApplicationError(f"Unexpected critical error: {str(e_unexpected)}", config.JOB_STATUS_APP_FAILED_UNEXPECTED)
            return self._handle_manual_intervention(app_error)