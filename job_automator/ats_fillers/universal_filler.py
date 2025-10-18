# job_automator/ats_fillers/universal_filler.py
"""
Universal ATS Filler - Works with ANY job application platform
Uses AI and intelligent form detection to fill applications automatically
"""
import logging
import time
import json
import re
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, ElementClickInterceptedException
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from .base_filler import BaseFiller, ApplicationError
import config

try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class UniversalFiller(BaseFiller):
    """
    Universal ATS Filler that works with ANY job application platform.
    Uses intelligent form detection and AI to handle any ATS.
    """

    def __init__(self, driver: WebDriver, job_data: dict, user_profile: dict,
                 document_paths: dict, credentials=None):
        """Initialize the Universal Filler"""
        super().__init__(driver, job_data, user_profile, document_paths, credentials)
        self.logger = logging.getLogger(__name__)

        # Get application URL from job data
        self.application_url = job_data.get('application_url', '')
        if not self.application_url:
            self.logger.error(f"{self.log_prefix}No application_url found in job_data!")

        self.logger.info(f"{self.log_prefix}Universal Filler Initialized - Works with ANY ATS")

        # Setup AI if available
        self.ai_model = None
        if AI_AVAILABLE and hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=config.GEMINI_API_KEY)
                self.ai_model = genai.GenerativeModel(
                    model_name=config.GEMINI_MODEL_NAME,
                    generation_config={"temperature": 0.3, "max_output_tokens": 2048}
                )
                self.logger.info(f"{self.log_prefix}AI assistance enabled")
            except Exception as e:
                self.logger.warning(f"{self.log_prefix}AI not available: {e}")

    def navigate_to_start(self) -> bool:
        """Navigate to the job application URL"""
        try:
            self.logger.info(f"{self.log_prefix}Navigating to application...")
            self.driver.get(self.application_url)
            time.sleep(3)
            return True
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Navigation failed: {e}")
            return False

    def apply(self) -> str:
        """Main application flow - works with any ATS"""
        try:
            self.logger.info(f"{self.log_prefix}Starting universal application process...")

            # Navigate to job
            if not self.navigate_to_start():
                raise ApplicationError("Failed to navigate", config.JOB_STATUS_APP_FAILED_ATS)

            # Try to start application
            if not self._click_apply_button():
                self.logger.warning(f"{self.log_prefix}No apply button found, assuming already on form")

            time.sleep(2)

            # Process application in steps
            max_steps = 20
            for step in range(1, max_steps + 1):
                self.logger.info(f"{self.log_prefix}Processing step {step}/{max_steps}")

                # Check if we're done
                if self._check_completion():
                    self.logger.info(f"{self.log_prefix}Application completed successfully!")
                    return config.JOB_STATUS_APPLIED_SUCCESS

                # Fill current page
                self._fill_current_page()

                # Try to advance
                if not self._click_next_button():
                    self.logger.warning(f"{self.log_prefix}No next button, checking for submit...")
                    if self._click_submit_button():
                        time.sleep(3)
                        if self._check_completion():
                            return config.JOB_STATUS_APPLIED_SUCCESS
                    break

                time.sleep(2)

            # If we got here, check one more time for completion
            if self._check_completion():
                return config.JOB_STATUS_APPLIED_SUCCESS

            # Application didn't complete successfully
            self.logger.warning(f"{self.log_prefix}Application may not have completed fully")
            return config.JOB_STATUS_APP_FAILED_ATS

        except ApplicationError as e:
            self.logger.error(f"{self.log_prefix}Application error: {e.message}")
            return e.status
        except Exception as e:
            self.logger.error(f"{self.log_prefix}Unexpected error: {e}", exc_info=True)
            return config.JOB_STATUS_APP_FAILED_ATS

    def _click_apply_button(self) -> bool:
        """Find and click the apply button"""
        apply_patterns = [
            "//button[contains(translate(text(), 'APPLY', 'apply'), 'apply')]",
            "//a[contains(translate(text(), 'APPLY', 'apply'), 'apply')]",
            "//button[contains(@class, 'apply')]",
            "//a[contains(@class, 'apply')]",
            "//input[@type='submit' and contains(@value, 'Apply')]",
            "//button[contains(text(), 'Submit Application')]",
            "//a[contains(text(), 'Submit Application')]",
        ]

        for pattern in apply_patterns:
            try:
                elements = self.driver.find_elements(By.XPATH, pattern)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        self.logger.info(f"{self.log_prefix}Found apply button")
                        elem.click()
                        return True
            except:
                continue

        return False

    def _fill_current_page(self):
        """Intelligently fill all fields on the current page"""
        self.logger.info(f"{self.log_prefix}Analyzing and filling current page...")

        # Upload documents first if possible
        self._upload_documents()

        # Find and fill all input fields
        self._fill_text_inputs()

        # Handle dropdowns/selects
        self._fill_dropdowns()

        # Handle textareas
        self._fill_textareas()

        # Handle checkboxes/radios
        self._handle_checkboxes_radios()

    def _upload_documents(self):
        """Upload resume and cover letter if file inputs found"""
        try:
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")

            for file_input in file_inputs:
                if not file_input.is_displayed():
                    continue

                # Determine if it's for resume or cover letter
                context = self._get_element_context(file_input)

                if any(keyword in context for keyword in ['resume', 'cv', 'curriculum']):
                    resume_path = self.document_paths.get('resume')
                    if resume_path and Path(resume_path).exists():
                        self.logger.info(f"{self.log_prefix}Uploading resume...")
                        file_input.send_keys(str(Path(resume_path).absolute()))
                        time.sleep(1)

                elif any(keyword in context for keyword in ['cover', 'letter']):
                    cl_path = self.document_paths.get('cover_letter')
                    if cl_path and Path(cl_path).exists():
                        self.logger.info(f"{self.log_prefix}Uploading cover letter...")
                        file_input.send_keys(str(Path(cl_path).absolute()))
                        time.sleep(1)

        except Exception as e:
            self.logger.debug(f"{self.log_prefix}Document upload: {e}")

    def _fill_text_inputs(self):
        """Fill all text input fields intelligently"""
        try:
            inputs = self.driver.find_elements(By.XPATH,
                "//input[@type='text' or @type='email' or @type='tel' or not(@type)]")

            for input_elem in inputs:
                if not input_elem.is_displayed() or not input_elem.is_enabled():
                    continue

                # Skip if already filled
                if input_elem.get_attribute('value'):
                    continue

                # Determine what this field is for
                field_type = self._identify_field_type(input_elem)
                value = self._get_value_for_field(field_type)

                if value:
                    try:
                        input_elem.clear()
                        input_elem.send_keys(value)
                        self.logger.debug(f"{self.log_prefix}Filled {field_type}: {value[:20]}...")
                    except:
                        pass

        except Exception as e:
            self.logger.debug(f"{self.log_prefix}Text input filling: {e}")

    def _fill_dropdowns(self):
        """Handle all dropdown/select elements"""
        try:
            selects = self.driver.find_elements(By.TAG_NAME, "select")

            for select_elem in selects:
                if not select_elem.is_displayed() or not select_elem.is_enabled():
                    continue

                try:
                    select = Select(select_elem)

                    # Skip if already selected
                    if select.first_selected_option.get_attribute('value'):
                        continue

                    # Determine what to select
                    field_type = self._identify_field_type(select_elem)
                    self._smart_select(select, field_type)

                except Exception as e:
                    self.logger.debug(f"{self.log_prefix}Dropdown: {e}")

        except Exception as e:
            self.logger.debug(f"{self.log_prefix}Dropdown filling: {e}")

    def _fill_textareas(self):
        """Fill textarea fields with AI assistance"""
        try:
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")

            for textarea in textareas:
                if not textarea.is_displayed() or not textarea.is_enabled():
                    continue

                # Skip if already filled
                if textarea.get_attribute('value') or textarea.text:
                    continue

                # Get context and generate appropriate text
                context = self._get_element_context(textarea)
                value = self._generate_text_response(context)

                if value:
                    try:
                        textarea.clear()
                        textarea.send_keys(value)
                        self.logger.debug(f"{self.log_prefix}Filled textarea")
                    except:
                        pass

        except Exception as e:
            self.logger.debug(f"{self.log_prefix}Textarea filling: {e}")

    def _handle_checkboxes_radios(self):
        """Handle checkboxes and radio buttons intelligently"""
        try:
            # Handle EEO/diversity questions - select "prefer not to answer"
            radios = self.driver.find_elements(By.XPATH, "//input[@type='radio']")

            for radio in radios:
                if not radio.is_displayed():
                    continue

                context = self._get_element_context(radio)

                # For EEO questions, prefer "decline" or "prefer not"
                if any(kw in context for kw in ['race', 'gender', 'veteran', 'disability', 'ethnicity']):
                    label_text = context.lower()
                    if any(phrase in label_text for phrase in ['decline', 'prefer not', 'choose not']):
                        try:
                            if not radio.is_selected():
                                radio.click()
                                time.sleep(0.3)
                        except:
                            pass

        except Exception as e:
            self.logger.debug(f"{self.log_prefix}Checkbox/radio handling: {e}")

    def _identify_field_type(self, element: WebElement) -> str:
        """Identify what type of information a field expects"""
        context = self._get_element_context(element).lower()

        # Name fields
        if any(kw in context for kw in ['first name', 'firstname', 'given name']):
            return 'first_name'
        if any(kw in context for kw in ['last name', 'lastname', 'surname', 'family name']):
            return 'last_name'
        if 'full name' in context or context.strip() == 'name':
            return 'full_name'

        # Contact fields
        if 'email' in context:
            return 'email'
        if any(kw in context for kw in ['phone', 'telephone', 'mobile', 'cell']):
            return 'phone'

        # Address fields
        if any(kw in context for kw in ['address', 'street']):
            return 'address'
        if 'city' in context:
            return 'city'
        if any(kw in context for kw in ['state', 'province', 'region']):
            return 'state'
        if any(kw in context for kw in ['zip', 'postal', 'postcode']):
            return 'zip'
        if 'country' in context:
            return 'country'

        # Professional fields
        if any(kw in context for kw in ['linkedin', 'linked in']):
            return 'linkedin'
        if any(kw in context for kw in ['github', 'portfolio', 'website']):
            return 'website'

        return 'unknown'

    def _get_value_for_field(self, field_type: str) -> str:
        """Get the appropriate value for a field type"""
        mapping = {
            'first_name': self.user_profile.get('first_name', config.FIRST_NAME),
            'last_name': self.user_profile.get('last_name', config.LAST_NAME),
            'full_name': self.user_profile.get('full_name', config.YOUR_NAME),
            'email': self.user_profile.get('email', config.YOUR_EMAIL),
            'phone': self.user_profile.get('phone', config.YOUR_PHONE),
            'linkedin': self.user_profile.get('linkedin', config.YOUR_LINKEDIN_URL or ''),
            'website': self.user_profile.get('website', config.WEBSITE or ''),
            'location': self.user_profile.get('location', config.LOCATION or ''),
            'city': config.LOCATION.split(',')[0] if hasattr(config, 'LOCATION') and config.LOCATION else '',
            'state': config.LOCATION.split(',')[-1].strip() if hasattr(config, 'LOCATION') and config.LOCATION else '',
        }

        return mapping.get(field_type, '')

    def _smart_select(self, select: Select, field_type: str):
        """Intelligently select dropdown option"""
        try:
            options = select.options

            # For EEO questions, select "prefer not to answer"
            if any(kw in field_type for kw in ['race', 'gender', 'veteran', 'disability']):
                for option in options:
                    text = option.text.lower()
                    if any(phrase in text for phrase in ['decline', 'prefer not', 'choose not']):
                        select.select_by_visible_text(option.text)
                        return

            # For country, select US
            if 'country' in field_type:
                for option in options:
                    if 'united states' in option.text.lower() or option.get_attribute('value') == 'US':
                        select.select_by_visible_text(option.text)
                        return

            # Default: select first non-empty option
            if len(options) > 1:
                select.select_by_index(1)

        except Exception as e:
            self.logger.debug(f"{self.log_prefix}Smart select: {e}")

    def _get_element_context(self, element: WebElement) -> str:
        """Get contextual information about an element"""
        context_parts = []

        try:
            # Get nearby label
            elem_id = element.get_attribute('id')
            if elem_id:
                labels = self.driver.find_elements(By.XPATH, f"//label[@for='{elem_id}']")
                for label in labels:
                    context_parts.append(label.text)

            # Get placeholder
            placeholder = element.get_attribute('placeholder')
            if placeholder:
                context_parts.append(placeholder)

            # Get name attribute
            name = element.get_attribute('name')
            if name:
                context_parts.append(name)

            # Get aria-label
            aria_label = element.get_attribute('aria-label')
            if aria_label:
                context_parts.append(aria_label)

            # Get parent text
            try:
                parent = element.find_element(By.XPATH, '..')
                parent_text = parent.text
                if parent_text and len(parent_text) < 100:
                    context_parts.append(parent_text)
            except:
                pass

        except:
            pass

        return ' '.join(context_parts).lower()

    def _generate_text_response(self, context: str) -> str:
        """Generate appropriate text response using AI if available"""
        # Common responses for typical questions
        if 'why' in context and any(kw in context for kw in ['work', 'join', 'interested']):
            return f"I am excited about this opportunity because it aligns with my skills and career goals. I believe I can contribute significantly to the team's success."

        if 'cover letter' in context:
            return "Please see attached cover letter document."

        if 'additional' in context or 'comments' in context:
            return "Thank you for considering my application. I look forward to discussing this opportunity further."

        # Use AI if available
        if self.ai_model:
            try:
                prompt = f"Generate a brief, professional response (2-3 sentences) for a job application question: '{context}'"
                response = self.ai_model.generate_content(prompt)
                return response.text[:500]
            except:
                pass

        return ""

    def _click_next_button(self) -> bool:
        """Find and click next/continue button"""
        next_patterns = [
            "//button[contains(translate(text(), 'NEXT', 'next'), 'next')]",
            "//button[contains(translate(text(), 'CONTINUE', 'continue'), 'continue')]",
            "//a[contains(translate(text(), 'NEXT', 'next'), 'next')]",
            "//a[contains(translate(text(), 'CONTINUE', 'continue'), 'continue')]",
            "//button[contains(@class, 'next')]",
            "//button[contains(@class, 'continue')]",
            "//input[@type='submit' and contains(@value, 'Next')]",
            "//input[@type='submit' and contains(@value, 'Continue')]",
            "//button[@type='submit']",
        ]

        for pattern in next_patterns:
            try:
                elements = self.driver.find_elements(By.XPATH, pattern)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        text = elem.text.lower()
                        # Skip submit buttons at this stage
                        if 'submit' in text and 'next' not in text:
                            continue

                        self.logger.info(f"{self.log_prefix}Clicking next button")
                        elem.click()
                        time.sleep(1)
                        return True
            except:
                continue

        return False

    def _click_submit_button(self) -> bool:
        """Find and click submit button"""
        submit_patterns = [
            "//button[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]",
            "//input[@type='submit' and contains(@value, 'Submit')]",
            "//button[contains(@class, 'submit')]",
            "//a[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]",
        ]

        for pattern in submit_patterns:
            try:
                elements = self.driver.find_elements(By.XPATH, pattern)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        self.logger.info(f"{self.log_prefix}Clicking submit button")
                        elem.click()
                        return True
            except:
                continue

        return False

    def _check_completion(self) -> bool:
        """Check if application was completed successfully"""
        success_indicators = [
            'thank you',
            'application submitted',
            'application received',
            'successfully submitted',
            'confirmation',
            'we have received your application',
            'application complete',
        ]

        page_text = self.driver.page_source.lower()

        for indicator in success_indicators:
            if indicator in page_text:
                self.logger.info(f"{self.log_prefix}Found completion indicator: {indicator}")
                return True

        # Check URL for success patterns
        current_url = self.driver.current_url.lower()
        if any(pattern in current_url for pattern in ['success', 'confirmation', 'thank', 'complete']):
            return True

        return False

    def fill_basic_info(self) -> bool:
        """Required by base class"""
        return True

    def upload_documents(self) -> bool:
        """Required by base class"""
        return True

    def answer_custom_questions(self) -> bool:
        """Required by base class"""
        return True

    def review_and_submit(self) -> bool:
        """Required by base class"""
        return True
