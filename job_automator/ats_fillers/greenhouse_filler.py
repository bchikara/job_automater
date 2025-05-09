# job_automator/ats_fillers/greenhouse_filler.py

import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from .base_filler import BaseFiller, ApplicationError
import config

# Add these MongoDB imports (if using MongoDB)
from datetime import datetime, date
import json
from bson import ObjectId
from typing import Any

try:
    from bson import ObjectId
    HAS_MONGO = True
except ImportError:
    HAS_MONGO = False
    ObjectId = type('ObjectId', (), {})


class GreenhouseFiller(BaseFiller):
    """Complete Greenhouse implementation with chunked AI processing"""
    
    logger = logging.getLogger(__name__)

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

    def _validate_job_id(self, job_id) -> str:
        """Handle various ID formats including MongoDB ObjectId"""
        try:
            if hasattr(__import__('bson'), 'ObjectId') and isinstance(job_id, ObjectId):
                return str(job_id)
            return str(job_id) if job_id else "unknown_id"
        except Exception:
            return "unknown_id"
        
    def _safe_json_dumps(self, data: Any, max_length: int = 2000) -> str:
        """Safely convert data to JSON with length limit"""
        try:
            return json.dumps(self._safe_serialize(data))[:max_length]
        except Exception as e:
            self.logger.warning(f"JSON serialization warning: {str(e)}")
            return "{}"

    def fill_basic_info(self) -> bool:
        """AI-powered basic info filling with chunked processing"""
        try:
            form = self.find_element(self.LOCATORS["application_form"], fatal=True)
            form_html = form.get_attribute('outerHTML')

            # Prompt template will now expect BaseFiller to provide {{profile}} and {{job}}
            # The actual profile_json and job_json are prepared by the overridden methods
            # called within BaseFiller.analyze_large_html_with_ai
            prompt = """Analyze this form chunk and identify fields to fill. Focus on:
- Personal info (name, email, phone)
- Professional info (LinkedIn, GitHub)
- Location details

For each field:
1. Provide exact locator (prefer id/name, fallback to XPath)
2. Mark if required
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
            
            analysis = self.analyze_large_html_with_ai(
                form_html,
                prompt, # This prompt template now has {{profile}} and {{job}}
                cache_key=f"basic_info_{self._validate_job_id(self.job_data.get('job_id'))}"
            )
            self._form_analysis = analysis
            return self._execute_field_instructions(analysis.get("fields", []))
        except Exception as e:
            self.logger.error(f"Basic info filling failed: {str(e)}", exc_info=True)
            return False
        
    def upload_documents(self) -> bool:
        """Handle document uploads with AI assistance if needed"""
        try:
            # Resume (required)
            resume_path = self.document_paths.get("resume")
            if not resume_path:
                raise ApplicationError("No resume path provided")
                
            if not self._upload_resume(resume_path):
                return False
                
            # Cover letter (optional)
            if "cover_letter" in self.document_paths:
                self._upload_cover_letter(self.document_paths["cover_letter"])
                
            return True
        except Exception as e:
            self.logger.error(f"Document upload failed: {str(e)}")
            return False

    def answer_custom_questions(self) -> bool:
        """AI-powered custom question answering"""
        try:
            # First handle standard EEO questions
            self._handle_eeo_questions()
            
            # Then analyze custom questions with AI
            questions_section = self.find_element(
                (By.XPATH, "//div[contains(@class, 'custom-questions')]"),
                wait_time=5,
                fatal=False
            )
            
            if questions_section:
                return self._handle_custom_questions_with_ai(questions_section)
            return True
        except Exception as e:
            self.logger.error(f"Custom questions failed: {str(e)}")
            return False

    def review_and_submit(self) -> bool:
        """Final review and submission"""
        try:
            # Scroll through form to trigger any validation
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # Submit application
            submit_button = (By.XPATH, "//button[contains(., 'Submit Application')]")
            if not self.click_element(submit_button, wait_time=15, fatal=True):
                return False
                
            # Verify submission
            time.sleep(3)
            return bool(self.find_element(
                self.LOCATORS["confirmation_message"],
                wait_time=10
            ))
        except Exception as e:
            self.logger.error(f"Submission failed: {str(e)}")
            return False

    # AI-powered implementation details
    def _execute_field_instructions(self, fields: List[Dict]) -> bool:
        """Execute field filling instructions from AI"""
        success = True
        for field in fields:
            try:
                handler_name = self.FIELD_HANDLERS.get(field.get("type"))
                if not handler_name:
                    self.logger.warning(f"No handler for field type: {field.get('type')}")
                    continue
                    
                handler = getattr(self, handler_name)
                if not handler(field):
                    self.logger.warning(f"Failed to fill field: {field.get('label')}")
                    success = False
            except Exception as e:
                self.logger.error(f"Error processing field {field.get('label')}: {str(e)}")
                success = False
        return success
    
    def _safe_serialize(self, data: Any) -> Any:
        """Convert non-JSON-serializable objects to serializable formats."""
        if isinstance(data, ObjectId):
            self.logger.debug(f"{self.log_prefix}GreenhouseFiller._safe_serialize: Converting ObjectId '{str(data)}' to string.")
            return str(data)
        elif isinstance(data, dict):
            return {k: self._safe_serialize(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._safe_serialize(v) for v in data]
        elif hasattr(data, '__dict__'):
            return self._safe_serialize(data.__dict__)
        elif isinstance(data, (datetime, date)):
            return data.isoformat() # Standard ISO format is generally better
        return data
    
    # Override methods from BaseFiller
    def _get_safe_profile_json_for_prompt(self) -> str:
        self.logger.debug(f"{self.log_prefix}GreenhouseFiller: Overriding _get_safe_profile_json_for_prompt. Using self._safe_json_dumps.")
        self.logger.debug(f"{self.log_prefix}GreenhouseFiller: user_profile before _safe_json_dumps (first 200 chars): {str(self.user_profile)[:200]}")
        serialized_profile_data = self._safe_json_dumps(self.user_profile, max_length=self.MAX_HTML_CHUNK_SIZE) # Use appropriate max_length
        self.logger.debug(f"{self.log_prefix}GreenhouseFiller: user_profile after _safe_json_dumps (first 200 chars): {serialized_profile_data[:200]}")
        return serialized_profile_data

    def _get_safe_job_json_for_prompt(self) -> str:
        self.logger.debug(f"{self.log_prefix}GreenhouseFiller: Overriding _get_safe_job_json_for_prompt. Using self._safe_json_dumps.")
        job_id_val = self.job_data.get('job_id')
        if isinstance(job_id_val, ObjectId): # Check actual type
            self.logger.info(f"{self.log_prefix}GreenhouseFiller: job_data contains ObjectId for job_id: {job_id_val}")
        self.logger.debug(f"{self.log_prefix}GreenhouseFiller: job_data before _safe_json_dumps (first 200 chars): {str(self.job_data)[:200]}")
        serialized_job_data = self._safe_json_dumps(self.job_data, max_length=self.MAX_HTML_CHUNK_SIZE) # Use appropriate max_length
        self.logger.debug(f"{self.log_prefix}GreenhouseFiller: job_data after _safe_json_dumps (first 200 chars): {serialized_job_data[:200]}")
        return serialized_job_data
    
    def _handle_eeo_questions(self) -> bool:
        """Standard EEO question handling"""
        decline_options = [
            (By.XPATH, "//*[contains(., 'decline to self-identify')]"),
            (By.XPATH, "//*[contains(., 'prefer not to say')]"),
            (By.XPATH, "//*[contains(., 'choose not to disclose')]")
        ]
        
        success = True
        for option in decline_options:
            if self.find_element(option, wait_time=1, fatal=False):
                success &= self.click_element(option, desc="Decline Option")
        return success

    def _handle_custom_questions_with_ai(self, section: WebElement) -> bool:
        """Analyze and answer custom questions with chunked AI processing"""
        section_html = section.get_attribute('outerHTML')
        
        prompt = """Analyze these custom job application questions:
        
        Job Requirements:
        {job}
        
        Applicant Profile:
        {profile}
        
        Previous Summary:
        {summary}
        
        Questions HTML Chunk ({chunk_num}/{total_chunks}):
        {chunk}
        
        For each question:
        1. Identify question type (text, multiple choice, etc.)
        2. Provide exact locator
        3. Generate answer based on profile/job
        4. Mark sensitive questions for 'prefer not to say'
        
        Return JSON format:
        {{
            "questions": [
                {{
                    "text": "What is your salary expectation?",
                    "type": "text",
                    "locator": ["xpath", "//input[@name='salary']"],
                    "answer": "$120,000 annually",
                    "source": "generated",
                    "sensitive": false
                }}
            ],
            "summary": "Processed salary and availability questions"
        }}"""
        
        analysis = self.analyze_large_html_with_ai(
            section_html,
            prompt,
            cache_key=f"custom_questions_{self.job_data.get('job_id')}"
        )
        
        return self._answer_questions(analysis.get("questions", []))

    # Field type handlers
    def _fill_text_field(self, field: Dict) -> bool:
        """Handle text input fields"""
        if not isinstance(field, dict):
            self.logger.error("Invalid field format")
            return None
        value = self._get_field_value(field)
        if value is None:
            return False
            
        return self.type_text(
            tuple(field["locator"]),
            value,
            desc=field.get("label", "text field"),
            fatal=field.get("required", False)
        )

    def _fill_select_field(self, field: Dict) -> bool:
        """Handle dropdown/select fields"""
        value = self._get_field_value(field)
        if value is None:
            return False
            
        return self.select_dropdown_option(
            tuple(field["locator"]),
            option_text=value,
            desc=field.get("label", "dropdown")
        )

    # ... [Implement other field type handlers]

    def _get_field_value(self, field: Dict) -> Optional[str]:
        """Get appropriate value for a field with fallback logic"""
        if field.get("source") == "prefer_not":
            if self._select_prefer_not_option(field):
                return None  # Already handled
            return "Prefer not to say"
            
        if field.get("value"):
            return field["value"]
            
        if field.get("required", False):
            return self._generate_field_value(field)
            
        return None

    def _select_prefer_not_option(self, field: Dict) -> bool:
        """Attempt to select 'prefer not to say' option"""
        prefer_not = (By.XPATH, "//*[contains(., 'prefer not to say') or contains(., 'decline to answer')]")
        return self.click_element(prefer_not, desc="Prefer not to say")

    def _generate_field_value(self, field: Dict) -> str:
        """Generate value for a field using AI"""
        prompt = f"""Generate appropriate value for this form field:
        
        Field Label: {field.get("label", "Unknown")}
        Field Type: {field.get("type", "text")}
        Required: {field.get("required", False)}
        
        Job Title: {self.job_data.get("title", "Unknown")}
        Company: {self.job_data.get("company", "Unknown")}
        
        Return just the value to use, no explanation needed."""
        
        response = self.llm.invoke(prompt)
        return response.content.strip()

    # Document handling
    def _upload_resume(self, resume_path: str) -> bool:
        """Handle resume upload with AI-assisted locator if needed"""
        if self.find_element(self.DEFAULT_FILE_INPUT_LOCATOR, wait_time=3, fatal=False):
            return self.upload_file(self.DEFAULT_FILE_INPUT_LOCATOR, resume_path, desc="Resume")
        # First try standard resume input
        # resume_input = (By.XPATH, "//input[@type='file' and contains(@accept, 'pdf')]")
        # if self.find_element(resume_input, wait_time=3, fatal=False):
        #     return self.upload_file(resume_input, resume_path, desc="Resume")
            
        # Fallback to AI locator discovery
        form_html = self.find_element(self.LOCATORS["application_form"]).get_attribute('outerHTML')
        prompt = """Identify the resume upload field in this form:
        
        {chunk}
        
        Return JSON with:
        {{
            "locator": ["xpath", "..."],
            "file_types": ["pdf", "docx"]
        }}"""
        
        result = self.analyze_large_html_with_ai(form_html, prompt)
        if result.get("locator"):
            return self.upload_file(
                tuple(result["locator"]),
                resume_path,
                desc="Resume (AI-identified)"
            )
            
        raise ApplicationError("Could not locate resume upload field")
    
    def navigate_to_start(self) -> bool:
        """Navigate to the application start URL"""
        if not self.job_data.get('application_url'):
            raise ApplicationError("No application URL provided in job data")
        return self.navigate(self.job_data['application_url'])

    def _fill_radio_field(self, field: Dict) -> bool:
        """Handle radio button fields"""
        return self.click_element(
            tuple(field["locator"]),
            desc=field.get("label", "radio option")
        )

    def _fill_checkbox_field(self, field: Dict) -> bool:
        """Handle checkbox fields"""
        return self.click_element(
            tuple(field["locator"]),
            desc=field.get("label", "checkbox")
        )

    def _fill_file_field(self, field: Dict) -> bool:
        """Handle file upload fields"""
        file_path = self.document_paths.get(field.get("document_type", ""))
        if not file_path:
            self.logger.warning(f"No file path for {field.get('label')}")
            return False
        return self.upload_file(
            tuple(field["locator"]),
            file_path,
            desc=field.get("label", "file input")
        )

    def _upload_cover_letter(self, cover_letter_path: str) -> bool:
        """Handle cover letter upload"""
        cl_input = (By.XPATH, "//input[@type='file' and contains(@accept, 'pdf')]")
        if self.find_element(cl_input, wait_time=3, fatal=False):
            return self.upload_file(cl_input, cover_letter_path, desc="Cover Letter")
        return False

    def _answer_questions(self, questions: List[Dict]) -> bool:
        """Answer questions from AI analysis"""
        success = True
        for question in questions:
            try:
                if question.get("type") == "text":
                    success &= self.type_text(
                        tuple(question["locator"]),
                        question["answer"],
                        desc=question.get("text", "question")
                    )
                elif question.get("type") in ["radio", "checkbox"]:
                    success &= self.click_element(
                        tuple(question["locator"]),
                        desc=question.get("text", "option")
                    )
            except Exception as e:
                self.logger.error(f"Failed to answer question: {str(e)}")
                success = False
        return success

    def apply(self) -> str:
        """Complete application flow with enhanced error handling"""
        try:
            self._ai_cache.clear()  # Clear previous analysis
            
            if not self.navigate_to_start():
                raise ApplicationError("Failed to navigate to application")
                
            steps = [
                ("Basic info", self.fill_basic_info),
                ("Documents", self.upload_documents),
                ("Questions", self.answer_custom_questions),
                ("Submission", self.review_and_submit)
            ]
            
            for step_name, step_func in steps:
                if not step_func():
                    raise ApplicationError(f"{step_name} step failed")
                
            return config.JOB_STATUS_APPLIED_SUCCESS
            
        except ApplicationError as e:
            self.logger.error(f"Application failed: {e.message}")
            return e.status
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return config.JOB_STATUS_APP_FAILED_ATS