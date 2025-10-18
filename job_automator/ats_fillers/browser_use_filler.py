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
        """Create intelligent task for AI agent with error handling"""

        # Get resume path for file upload
        resume_path = user_info.get('resume_path', '')
        cover_letter_path = user_info.get('cover_letter_path', '')

        # Get job and company info for intelligent answers
        job_title = self.job_data.get('job_title', 'this position')
        company_name = self.job_data.get('company_name', 'your company')
        job_description = self.job_data.get('job_description', '')[:500]  # First 500 chars

        task = f"""
Go to {self.job_data.get('application_url')} and fill the job application form.

MY BASIC INFO:
Name: {user_info['first_name']} {user_info['last_name']}
Email: {user_info['email']}
Phone: {user_info['phone']}
Location: {user_info['city']}, {user_info['state']} {user_info['zip_code']}
LinkedIn: {user_info['linkedin']}
Resume File: {resume_path}
Cover Letter File: {cover_letter_path}

JOB CONTEXT:
Position: {job_title}
Company: {company_name}
Job Description (excerpt): {job_description}

MY BACKGROUND & EXPERIENCE:
- {config.JOB_TITLE_CURRENT} with {config.YEARS_EXPERIENCE}+ years experience
- Tech Stack: {config.TECH_STACK}
- {config.KEY_ACHIEVEMENT}
- Experience with {config.SPECIALIZATIONS}
- {config.SOFT_SKILLS}
- Passionate about {config.CAREER_PASSION}

Login credentials if needed:
Email: {user_info['email']}
Password: {config.YOUR_PASSWORD}

STEP-BY-STEP INSTRUCTIONS:
1. SCROLL DOWN to see all page elements
2. Click "Apply" or "Start Application" button
3. CHECK ALL agreement checkboxes ("I agree", "I consent", "I accept terms")
4. Login if required (use credentials above)
5. Fill ALL form fields with my info
   ⚠️ CRITICAL FOR EVERY FIELD:
   - FIRST: Read the field LABEL above or beside the input box
   - SECOND: Look at placeholder text inside the field
   - THIRD: Determine what VALUE from MY BASIC INFO matches this label
   - FOURTH: Fill with the CORRECT value for that specific field
   - Example: If label says "First Name", use ONLY first name (not full name!)
   - Example: If label says "City", use ONLY city (not full address!)
   - Example: If label says "Last Name", use ONLY last name (not full name!)
6. For DATE fields (start date, availability, etc.):
   - IMPORTANT: Most date fields expect MM/DD/YYYY format (US format)
   - If asked for "start date" or "availability date", use: 12/17/2025
   - If asked for "earliest start date", use: 12/17/2025
   - If the field has a date picker (calendar icon):
     * Click the date picker icon to open calendar
     * Navigate to December 2025
     * Click on day 17
   - If it's a text input:
     * Type: 12/17/2025
     * DO NOT type "17 december 2025" or "december 17, 2025"
   - After entering date, wait 1 second for field to process
   - Verify the date appears correctly in the field
7. For AUTOCOMPLETE fields (location, school, company, etc.):
   - ⚠️ CRITICAL: ONLY use values that match the field's purpose
   - These fields show suggestions as you type
   - STRATEGY:
     * First, READ the field label carefully (e.g., "City", "School", "Company")
     * Click the field to focus it
     * Type the CORRECT value for this field from MY BASIC INFO section
     * Example: If label says "City", type city from my location
     * Example: If label says "School", type my university/school name
     * Example: If label says "Company", type my current/previous company
     * Type the first few characters (e.g., "New Y" for New York)
     * WAIT 2-3 seconds for suggestions to appear
     * Look for a dropdown list of suggestions
     * Click the matching suggestion from the list
     * VERIFY the selected value matches the field purpose
     * DO NOT just type the full value and move on
   - ⚠️ VALIDATION: After selecting from dropdown:
     * Check if the field now shows a valid value
     * If field is still empty or shows wrong data, try again
     * If no dropdown appears after 3 seconds, SKIP this field
     * DO NOT put random values or values from other fields
   - Example for "City": Type "Los An" → wait → click "Los Angeles, CA" from dropdown
   - Example for "School": Type my school name → wait → click from suggestions
   - If autocomplete fails after 2 tries:
     * Leave the field EMPTY
     * DO NOT type random values
     * Move to next field
8. For regular dropdowns (non-autocomplete):
   - Click to open the dropdown
   - Wait 1 second for options to appear
   - Find and click the correct option
   - If option not found in DOM, try typing the value instead
9. For file uploads:
   - Click the file upload button/field
   - If you see a file selector, upload: {resume_path}
   - If resume upload fails, try clicking the upload button again
   - If it still fails after 2 attempts, continue without it
10. For CUSTOM QUESTIONS and TEXTAREAS (text boxes, "Why should we hire you?", etc.):
   ⚠️ CRITICAL TEXTAREA RULES - FOLLOW EXACTLY:

   BEFORE TOUCHING ANY TEXTAREA:
   1. Look at the textarea - does it have ANY text inside? (even 1 character)
   2. If YES → SKIP THIS FIELD COMPLETELY, move to next field
   3. If NO → Continue to step 4
   4. Check for character counter (e.g., "0/500", "max 200 characters", "Character count: 0")

   CHARACTER LIMIT DETECTION:
   - Look ABOVE the textarea for: "Max X characters", "X character limit"
   - Look BELOW the textarea for: "0/500", "0 of 500", "500 characters remaining"
   - Look INSIDE placeholder for: "Maximum 200 characters"
   - If you see a number like "0/500" or "500 characters remaining":
     * The limit is the second number (500 in this example)
     * Generate answer that is 20-30 chars SHORTER than limit
     * Example: Limit is 500 → Write 470 chars maximum
   - If NO limit visible: Default to 250 characters maximum (very safe)

   WRITING TO TEXTAREA:
   - Generate appropriate answer (use MY BACKGROUND & EXPERIENCE)
   - Keep it SHORT and SPECIFIC
   - Check length BEFORE typing (count your characters mentally)
   - Type the answer ONCE
   - After typing, IMMEDIATELY:
     * Look at character counter - does it show count went up?
     * Look at textarea - do you see your text?
     * If counter shows "470/500" and you see your text → SUCCESS
     * Move to NEXT field immediately

   AFTER FILLING TEXTAREA:
   - NEVER return to this textarea
   - If you see this textarea again (after scroll, page refresh):
     * Check: Does it have text? YES → SKIP IT
     * DO NOT type again
     * DO NOT try to "complete" it
     * Move on to other fields

   INCOMPLETE TEXT HANDLING:
   - If textarea cuts off your text (you see "..." or text is truncated):
     * This is NORMAL if you hit character limit
     * DO NOT try to type more
     * The field accepted what fit
     * Move to next field
   - If counter shows you hit the limit (e.g., "500/500"):
     * Perfect! You filled it completely
     * Move to next field

   STOPPING CONDITIONS (when to stop typing in textarea):
   - ✅ Counter reaches near limit (within 10 chars)
   - ✅ You see your full answer in the field
   - ✅ Field stops accepting more characters
   - ✅ Any text appears in the field (field is no longer empty)
   - Then IMMEDIATELY move to next field
11. SCROLL DOWN to see more fields
12. For "Next", "Save & Continue", "Continue" buttons:
    - WAIT 2 seconds after filling last field (let page settle)
    - SCROLL to make button visible
    - Click the button
    - If click fails with DOM error (element not found):
      * Wait 2 seconds
      * Refresh the page state by scrolling up then down
      * Find the button again (index may have changed)
      * Try clicking again
    - If still fails, try pressing Enter key instead
13. Before clicking Submit, verify ALL required fields are filled

📋 FIELD-BY-FIELD WORKFLOW - Follow this for EVERY field:

STEP 1: LOOK at the field
- Where is the label? (above field, beside field, or placeholder inside)
- What does the label say? ("First Name", "City", "Phone", etc.)

STEP 2: MATCH label to MY BASIC INFO
- First Name → {user_info['first_name']}
- Last Name → {user_info['last_name']}
- Email → {user_info['email']}
- Phone → {user_info['phone']}
- City → {user_info['city']} (NOT full address!)
- State → {user_info['state']} (NOT full location!)
- Zip Code → {user_info['zip_code']} (NOT included with city!)

STEP 3: FILL with the EXACT matching value
- Use ONLY the value that matches the label
- DO NOT use compound values (full address, full name) in single-part fields

STEP 4: VERIFY what appears in the field
- Does it match what the label asked for?
- If label said "City", does field show ONLY city name?
- If wrong, clear and fix

REAL EXAMPLES FROM YOUR SCREENSHOTS:

Example 1 - Name Fields:
Label: "First Name"
❌ WRONG: Type "Vipul Chikara" (full name)
✅ CORRECT: Type "{user_info['first_name']}" (first name only)

Label: "Last Name"
❌ WRONG: Type "Bhupesh Chikara" (keeping last name + something)
✅ CORRECT: Type "{user_info['last_name']}" (last name only)

Example 2 - Address Fields:
Label: "City"
❌ WRONG: Type "Syracuse, New York 13210" (full address)
✅ CORRECT: Type "{user_info['city']}" (city only)

Label: "State/Province"
❌ WRONG: Type "Syracuse, New York"
✅ CORRECT: Type "{user_info['state']}" or select from dropdown

Label: "Zip/Postal Code"
❌ WRONG: Type "New York 13210"
✅ CORRECT: Type "{user_info['zip_code']}" (zip only)

Example 3 - Phone Number:
Label: "Number" or "Phone"
❌ WRONG: Type email or other info
✅ CORRECT: Type "{user_info['phone']}"

FIELD TYPE EXAMPLES - How to handle specific field types:

📅 DATE FIELDS:
- Label: "Start Date", "Availability Date", "Earliest Start Date"
- ✅ CORRECT: Type "12/17/2025" (MM/DD/YYYY)
- ❌ WRONG: "17 december 2025", "2025-12-17", "december 17"
- For date pickers: Click calendar icon → navigate to Dec 2025 → click day 17

🔍 AUTOCOMPLETE FIELDS:
- Label: "City", "School", "Current Company", "Previous Company"
- ⚠️ CRITICAL RULE: Match field label to correct value from MY BASIC INFO
- Example - City field:
  * Read label: "City" or "Location"
  * Use city from MY BASIC INFO (not school name, not company!)
  * Click field
  * Type: First few chars of MY city (e.g., "Los An")
  * WAIT 2-3 seconds
  * Dropdown appears with: "Los Angeles, CA", "Los Angeles, TX", etc.
  * Click "Los Angeles, CA"
  * ✅ VERIFY: Field now shows "Los Angeles, CA"
  * ❌ WRONG: If field is empty or shows typed text without city format
- Example - School field:
  * Read label: "School", "University", "Education"
  * Use MY school/university name (not city, not company!)
  * Type: First few chars of school name
  * Wait for dropdown
  * Click matching suggestion
  * ✅ VERIFY: Field shows full validated school name
  * ❌ WRONG: Showing typed text instead of official school name
- Example - Company field:
  * Read label: "Company", "Employer", "Organization"
  * Use MY company name (not school, not city!)
  * Follow same autocomplete pattern
- ⚠️ IF WRONG VALUE APPEARS: Clear field and try again
- ⚠️ IF NO DROPDOWN AFTER 3s: Leave field EMPTY, move on

📝 TEXT FIELDS:
⚠️ NAME FIELDS - CRITICAL: Parse MY BASIC INFO correctly:
My info: Name: {user_info['first_name']} {user_info['last_name']}

Field Label → What to Fill:
- "First Name" → Use ONLY: {user_info['first_name']}
- "Preferred First Name" → Use ONLY: {user_info['first_name']}
- "Last Name" → Use ONLY: {user_info['last_name']}
- "Full Name" → Use: {user_info['first_name']} {user_info['last_name']}
- "Middle Name" → Leave empty or type "N/A"

❌ WRONG: Label says "First Name", you type full name
✅ CORRECT: Label says "First Name", you type ONLY first name

📍 ADDRESS FIELDS - CRITICAL: Parse location correctly:
My location: {user_info['city']}, {user_info['state']} {user_info['zip_code']}

Field Label → What to Fill:
- "Address" or "Street Address" → Use: {user_info['street']} (if provided)
- "City" → Use ONLY: {user_info['city']}
- "State" or "State/Province" → Use ONLY: {user_info['state']}
- "Zip" or "Postal Code" → Use ONLY: {user_info['zip_code']}
- "Country" → Use: United States or select from dropdown

❌ WRONG: Label says "City", you type full address with zip code
✅ CORRECT: Label says "City", you type ONLY the city name

📧 OTHER TEXT FIELDS:
- Email: Type exactly as provided
- Phone: Format as provided or (XXX) XXX-XXXX
- LinkedIn: Full URL (https://linkedin.com/in/username)

📋 DROPDOWN FIELDS (regular, not autocomplete):
- Label: "Gender", "Veteran Status", "Ethnicity"
- Click dropdown → wait 1s → click option
- If option not visible, try typing the first letter

ERROR RECOVERY - If submission fails:
1. READ the error message carefully
2. Look for missing required fields (usually marked with * or red text)
3. Check if file upload is required but missing
4. If resume/CV is required:
   - Find the resume upload button
   - Click it to open file selector
   - Upload the file: {resume_path}
5. If specific fields are missing, fill them
6. Check ALL "I agree" checkboxes again
7. Try Submit again
8. If it fails again, report the specific error

FILE UPLOAD HANDLING:
- Resume uploads often fail on first try
- If you see "Please upload resume" or "Resume required", you MUST retry:
  1. Find the resume upload button (might say "Upload Resume", "Choose File", "Browse")
  2. Click it
  3. When file selector opens, select: {resume_path}
  4. Verify the file name appears on the page
  5. Then continue filling the form

ANSWERING CUSTOM QUESTIONS - EXAMPLES:

Question: "What tech stack have you worked with?"
❌ BAD: "I have experience with various technologies and programming languages."
✅ GOOD: "I've worked extensively with Python (Django, FastAPI), JavaScript (React, Node.js), and AWS for deploying scalable applications. Recently built an automation system that processes 10K+ jobs daily."

Question: "Why should we hire you?"
❌ BAD: "I am a hard worker and quick learner who would be a great fit for your company."
✅ GOOD: "I bring 3+ years building production systems at scale. At my last role, I reduced processing time by 60% through smart architecture. I'm excited about {company_name} because your work in [mention something from job description] aligns with my experience in automation and efficiency."

Question: "Why do you want to work at {company_name}?"
❌ BAD: "Your company has a great reputation and I want to grow my career."
✅ GOOD: "I'm impressed by {company_name}'s approach to [mention from job description]. As someone who's built similar solutions with Python and AWS, I see opportunities to contribute immediately while learning from your team's expertise in [domain]."

Question: "Describe a challenging project"
❌ BAD: "I worked on many challenging projects that helped me learn new skills."
✅ GOOD: "Built a job application system that automates form filling using AI and browser automation. Overcame challenges with dynamic forms by implementing intelligent error recovery. It now handles 100+ applications with 70% success rate."

Question: "What's your experience with [specific tech]?"
❌ BAD: "I have good experience with that technology."
✅ GOOD: "Used [tech] for 2+ years building web applications. Most recently architected a microservices system handling 50K daily requests. Comfortable with deployment, optimization, and debugging in production."

KEY PRINCIPLES FOR ANSWERS:
1. Keep it SHORT (2-4 sentences, max 50 words)
2. Use SPECIFIC numbers/metrics when possible
3. Mention the COMPANY NAME naturally
4. Reference actual TECH STACK from my background
5. Sound CONVERSATIONAL (like you're talking to a person)
6. Each answer should be UNIQUE (don't repeat phrases)
7. Tie your experience to THEIR job description
8. Show ENTHUSIASM but don't oversell

CRITICAL RULES FOR SUCCESS:
- NEVER skip required fields
- ALWAYS check error messages and fix them
- File uploads are CRITICAL - retry up to 3 times if they fail
- If form says "required field missing", scroll through entire form to find it
- Don't give up on file uploads - they're essential for applications
- Generate UNIQUE, HUMAN answers for text questions - NO plagiarism
- Keep custom answers SHORT and SPECIFIC

⚠️ MOST COMMON MISTAKES TO AVOID:
1. ❌ Typing dates in wrong format (use MM/DD/YYYY only!)
2. ❌ Not waiting for autocomplete dropdowns to appear (MUST wait 2-3s)
3. ❌ Typing full value in autocomplete instead of clicking suggestion
4. ❌ Moving to next field before autocomplete selection completes
5. ❌ Skipping file uploads when they fail (must retry 3 times)
6. ❌ Not scrolling down to see all fields
7. ❌ Clicking Next/Submit before all fields are filled
8. ❌ FILLING TEXTAREAS MULTIPLE TIMES (check if already filled!)
9. ❌ Putting wrong values in autocomplete (city in school field, etc.)
10. ❌ Not verifying field value after filling
11. ❌ Going back to fields that are already complete

✅ BEST PRACTICES FOR RELIABILITY:
1. BEFORE filling any field: Check if it's already filled (look for text in the field)
2. If field already has text: SKIP it and move to next field
3. Always WAIT 1-2 seconds after filling a field (let it process)
4. For autocomplete: Type partial → Wait → Click suggestion → Wait → Verify
5. VERIFY after filling: Look at the field to confirm correct value appears
6. For textareas: Fill ONCE, then move on - NEVER go back to same field
7. After clicking Next/Submit, wait 3 seconds before deciding if it worked
8. If an action fails, try scrolling to the element first
9. Read error messages carefully - they tell you exactly what's missing
10. Keep track of which fields you've completed to avoid repeating work

📝 TEXTAREA DECISION TREE - Follow this EVERY time you see a textarea:

┌─ See textarea
│
├─ Question: Does it have ANY text inside?
│  ├─ YES → SKIP this field, move to next ✓
│  └─ NO → Continue
│
├─ Question: Do I see a character counter?
│  ├─ YES → Read the limit (e.g., "0/500" means 500 char limit)
│  │         Generate answer 20-30 chars shorter
│  └─ NO → Default to 250 characters maximum
│
├─ Action: Generate appropriate short answer
│  └─ Type it ONCE
│
├─ Question: Do I see my text in the field now?
│  ├─ YES → SUCCESS! Move to next field ✓
│  └─ NO → Check counter, if it went up, still success ✓
│
└─ NEVER return to this textarea

⚠️ IF YOU SEE THE SAME TEXTAREA AGAIN:
- Has text? → Already filled, SKIP ✓
- Empty? → Impossible if you just filled it
- Check carefully - you might be looking at a DIFFERENT textarea

🔍 FIELD VERIFICATION CHECKLIST:
Before moving to next field, verify:
✓ Text fields: Value matches what I typed
✓ Autocomplete: Selected suggestion appears in field (not just typed text)
✓ Textareas: My answer appears in full
✓ Dates: Shows MM/DD/YYYY format
✓ Dropdowns: Selected option is visible
✓ File uploads: Filename appears on page

📝 TEXTAREA CHARACTER LIMIT EXAMPLES:

Example 1 - Counter shows "0/500":
✅ CORRECT:
- Limit detected: 500 characters
- Generate answer: 470 characters (leaving buffer)
- Type once
- Counter shows: "470/500"
- See text in field? YES
- Move to next field ✓

❌ WRONG:
- Type 600 character answer
- Gets cut off at 500
- Try to type more
- Keep retyping
- Loop forever ✗

Example 2 - Counter shows "Max 200 characters":
✅ CORRECT:
- Limit detected: 200 characters
- Generate SHORT answer: 180 characters
- Type once
- Counter shows: "180/200"
- Move to next field ✓

❌ WRONG:
- Type long answer (300 chars)
- Field cuts off at 200
- See it's truncated
- Try to type again
- Endless loop ✗

Example 3 - NO counter visible:
✅ CORRECT:
- No limit seen
- Use DEFAULT: 250 characters max
- Generate 2-3 sentence answer (220 chars)
- Type once
- See text in field
- Move to next field ✓

Example 4 - Returning to filled textarea:
SCENARIO: You filled textarea, scrolled down, page refreshes, you scroll up
✅ CORRECT:
- See textarea again
- CHECK: Does it have text? YES
- SKIP this field ✓
- Move to next empty field ✓

❌ WRONG:
- See textarea again
- Think: "Maybe I should fill this"
- Type same answer again
- Now it has double text ✗

🚫 NEVER DO THIS:
- ❌ Fill a field that already has correct data
- ❌ Type in autocomplete without clicking dropdown suggestion
- ❌ Put city name in school field or school name in city field
- ❌ Keep typing in same textarea over and over
- ❌ Move to next field without verifying current field is correct
- ❌ Type FULL NAME when label says "First Name" or "Last Name"
- ❌ Type FULL ADDRESS when label says "City" or "State" or "Zip"
- ❌ Type compound values (with commas, multiple parts) in single-part fields
- ❌ Ignore the field label and just type whatever comes to mind
- ❌ Return to textarea that already has text and type again
- ❌ Try to "complete" a textarea that got cut off by character limit
- ❌ Generate answers longer than the character limit
- ❌ Keep typing when counter shows you hit the limit

⚠️ COMPOUND vs SINGLE VALUES - CRITICAL UNDERSTANDING:

COMPOUND VALUES (multiple parts together):
- Full Name: "{user_info['first_name']} {user_info['last_name']}"
- Full Address: "{user_info['street']}, {user_info['city']}, {user_info['state']} {user_info['zip_code']}"
- Full Location: "{user_info['city']}, {user_info['state']} {user_info['zip_code']}"

SINGLE VALUES (one part only):
- First Name: "{user_info['first_name']}" (NO last name)
- Last Name: "{user_info['last_name']}" (NO first name)
- City: "{user_info['city']}" (NO state, NO zip)
- State: "{user_info['state']}" (NO city, NO zip)
- Zip: "{user_info['zip_code']}" (NO city, NO state)

MATCHING RULE:
Label asks for SINGLE value → Use SINGLE value
Label asks for FULL/COMPLETE value → Use COMPOUND value

Examples:
- "First Name" = SINGLE → Use first name only
- "Full Name" = COMPOUND → Use first + last
- "City" = SINGLE → Use city only
- "Address" = COMPOUND → Use full address
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
