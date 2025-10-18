"""
Interactive Setup Wizard for Job Agent
Guides users through first-time configuration
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class SetupWizard:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / '.env'
        self.env_example = self.project_root / '.env.example'
        self.config = {}

    def print_header(self, text: str):
        """Print a styled header."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}  {text}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}\n")

    def print_section(self, text: str):
        """Print a section header."""
        print(f"\n{Colors.BLUE}{Colors.BOLD}{'─'*80}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'─'*80}{Colors.END}\n")

    def print_success(self, text: str):
        """Print success message."""
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")

    def print_error(self, text: str):
        """Print error message."""
        print(f"{Colors.RED}✗ {text}{Colors.END}")

    def print_warning(self, text: str):
        """Print warning message."""
        print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

    def print_info(self, text: str):
        """Print info message."""
        print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

    def get_input(self, prompt: str, default: str = "", required: bool = True,
                  validator: Optional[callable] = None, secret: bool = False) -> str:
        """
        Get user input with validation.

        Args:
            prompt: Question to ask user
            default: Default value
            required: Whether field is required
            validator: Optional validation function
            secret: Whether to hide input (for passwords)
        """
        while True:
            if default:
                display_prompt = f"{prompt} [{Colors.YELLOW}{default}{Colors.END}]: "
            else:
                display_prompt = f"{prompt}: "

            if secret:
                import getpass
                value = getpass.getpass(display_prompt)
            else:
                value = input(display_prompt).strip()

            # Use default if provided and no input given
            if not value and default:
                value = default

            # Check if required
            if required and not value:
                self.print_error("This field is required. Please enter a value.")
                continue

            # Run validator if provided
            if validator and value:
                is_valid, error_msg = validator(value)
                if not is_valid:
                    self.print_error(error_msg)
                    continue

            return value

    def get_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no input from user."""
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()

            if not response:
                return default

            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                self.print_error("Please enter 'y' or 'n'")

    def validate_email(self, email: str) -> tuple[bool, str]:
        """Validate email address."""
        if '@' in email and '.' in email.split('@')[-1]:
            return True, ""
        return False, "Invalid email format. Must contain @ and domain."

    def validate_phone(self, phone: str) -> tuple[bool, str]:
        """Validate phone number."""
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) >= 10:
            return True, ""
        return False, "Phone number must contain at least 10 digits."

    def validate_url(self, url: str, domain: str = "") -> tuple[bool, str]:
        """Validate URL."""
        if not url.startswith(('http://', 'https://')):
            return False, "URL must start with http:// or https://"
        if domain and domain.lower() not in url.lower():
            return False, f"URL must contain '{domain}'"
        return True, ""

    def validate_gemini_key(self, key: str) -> tuple[bool, str]:
        """Validate Gemini API key."""
        if len(key) > 20 and key.startswith('AI'):
            return True, ""
        return False, "Invalid Gemini API key format. Should start with 'AI' and be longer than 20 characters."

    def check_system_dependencies(self):
        """Check system dependencies before setup."""
        self.print_section("System Requirements Check")

        print(f"{Colors.CYAN}Checking your system for required dependencies...{Colors.END}\n")

        try:
            from system_checker import SystemChecker
            checker = SystemChecker()
            all_passed = checker.check_all(verbose=True)

            if not all_passed:
                self.print_error("Critical dependencies are missing!")
                print(f"\n{Colors.YELLOW}Please install the missing dependencies and run setup again.{Colors.END}")
                if not self.get_yes_no("Continue anyway? (not recommended)", default=False):
                    sys.exit(1)
        except ImportError:
            self.print_warning("Could not run system checks (system_checker.py not found)")
            print(f"{Colors.CYAN}Make sure you have:{Colors.END}")
            print("  • Python 3.8+")
            print("  • pip")
            print("  • MongoDB")
            print("  • LaTeX (pdflatex)")
            print()
            if not self.get_yes_no("Continue with setup?", default=True):
                sys.exit(0)

    def welcome(self):
        """Display welcome message."""
        self.print_header("WELCOME TO JOB AGENT SETUP WIZARD")
        print(f"{Colors.WHITE}This wizard will help you configure Job Agent for first-time use.{Colors.END}")
        print(f"{Colors.WHITE}You'll need about 10-15 minutes to complete the setup.{Colors.END}\n")

        print(f"{Colors.CYAN}What you'll need:{Colors.END}")
        print("  • Google Gemini API key (free)")
        print("  • Your personal and contact information")
        print("  • Your professional profile URLs (LinkedIn, GitHub)")
        print("  • Your education details")
        print("  • Your resume data (work experience, projects, skills)")

        print(f"\n{Colors.YELLOW}Note: All information will be stored locally in .env file{Colors.END}")
        print(f"{Colors.YELLOW}This file is automatically excluded from version control{Colors.END}\n")

        if not self.get_yes_no("Ready to begin?", default=True):
            print("\nSetup cancelled. Run 'python setup_wizard.py' when you're ready.")
            sys.exit(0)

    def setup_env_file(self):
        """Setup .env file."""
        self.print_section("Step 1: Environment File Setup")

        if self.env_file.exists():
            self.print_warning(f".env file already exists at: {self.env_file}")
            if not self.get_yes_no("Do you want to backup and replace it?", default=False):
                self.print_info("Keeping existing .env file. You can edit it manually.")
                return False

            # Backup existing file
            backup_path = self.env_file.with_suffix('.env.backup')
            shutil.copy(self.env_file, backup_path)
            self.print_success(f"Backed up existing .env to {backup_path}")

        # Copy from example
        if self.env_example.exists():
            shutil.copy(self.env_example, self.env_file)
            self.print_success("Created .env file from template")
            return True
        else:
            self.print_error(".env.example template not found!")
            return False

    def collect_api_credentials(self):
        """Collect API credentials."""
        self.print_section("Step 2: API Credentials")

        print(f"{Colors.CYAN}Google Gemini API Key{Colors.END}")
        print("The Gemini API is used for AI-powered resume tailoring and question answering.")
        print(f"Get your free API key here: {Colors.UNDERLINE}https://aistudio.google.com/app/apikey{Colors.END}\n")

        self.config['GEMINI_API_KEY'] = self.get_input(
            "Enter your Gemini API key",
            required=True,
            validator=self.validate_gemini_key,
            secret=True
        )

        # Optional: Ask about model preference
        print(f"\n{Colors.CYAN}Gemini Model Selection (optional){Colors.END}")
        print("  1. gemini-2.5-flash-lite (recommended - fast, high rate limits)")
        print("  2. gemini-1.5-flash (balanced)")
        print("  3. gemini-1.5-pro (most capable but slower)")

        model_choice = self.get_input("Select model (1-3)", default="1", required=False)
        models = {
            "1": "gemini-2.5-flash-lite",
            "2": "gemini-1.5-flash",
            "3": "gemini-1.5-pro"
        }
        self.config['GEMINI_MODEL_NAME'] = models.get(model_choice, "gemini-2.5-flash-lite")

    def collect_personal_info(self):
        """Collect personal information."""
        self.print_section("Step 3: Personal Information")

        self.config['YOUR_NAME'] = self.get_input("Full Name", required=True)

        # Auto-split name
        name_parts = self.config['YOUR_NAME'].split()
        default_first = name_parts[0] if name_parts else ""
        default_last = name_parts[-1] if len(name_parts) > 1 else ""

        self.config['FIRST_NAME'] = self.get_input("First Name", default=default_first, required=True)
        self.config['LAST_NAME'] = self.get_input("Last Name", default=default_last, required=True)

        self.config['YOUR_EMAIL'] = self.get_input(
            "Email Address",
            required=True,
            validator=self.validate_email
        )

        self.config['YOUR_PHONE'] = self.get_input(
            "Phone Number",
            required=True,
            validator=self.validate_phone
        )

    def collect_address(self):
        """Collect address information."""
        self.print_section("Step 4: Address")

        self.config['STREET_ADDRESS'] = self.get_input("Street Address", required=True)
        self.config['CITY'] = self.get_input("City", required=True)
        self.config['STATE'] = self.get_input("State/Province", required=True)
        self.config['ZIP_CODE'] = self.get_input("ZIP/Postal Code", required=True)

        # Auto-generate location
        default_location = f"{self.config['CITY']}, {self.config['STATE']}"
        self.config['LOCATION'] = self.get_input(
            "Location (as shown on resume)",
            default=default_location,
            required=True
        )

    def collect_professional_profiles(self):
        """Collect professional profile URLs."""
        self.print_section("Step 5: Professional Profiles")

        self.config['YOUR_LINKEDIN_PROFILE_URL'] = self.get_input(
            "LinkedIn Profile URL",
            required=True,
            validator=lambda url: self.validate_url(url, "linkedin.com")
        )

        self.config['YOUR_GITHUB_URL'] = self.get_input(
            "GitHub Profile URL",
            required=True,
            validator=lambda url: self.validate_url(url, "github.com")
        )

        self.config['WEBSITE'] = self.get_input(
            "Portfolio/Website URL (optional)",
            required=False,
            validator=lambda url: self.validate_url(url) if url else (True, "")
        )

        self.config['YOUR_LEETCODE_URL'] = self.get_input(
            "LeetCode Profile URL (optional)",
            required=False
        )

    def collect_work_authorization(self):
        """Collect work authorization information."""
        self.print_section("Step 6: Work Authorization")

        work_auth = self.get_yes_no("Are you authorized to work in the US?", default=True)
        self.config['WORK_AUTHORIZED'] = "Yes" if work_auth else "No"

        if work_auth:
            sponsor = self.get_yes_no("Do you require visa sponsorship?", default=False)
            self.config['REQUIRE_SPONSORSHIP'] = "Yes" if sponsor else "No"
        else:
            self.config['REQUIRE_SPONSORSHIP'] = "Yes"

    def collect_education(self):
        """Collect education information."""
        self.print_section("Step 7: Education")

        print(f"{Colors.CYAN}Enter your highest or most relevant degree.{Colors.END}")
        print(f"{Colors.CYAN}You can add more degrees later in base_resume.json{Colors.END}\n")

        self.config['UNIVERSITY'] = self.get_input(
            "University/College name",
            required=True
        )

        self.config['DEGREE'] = self.get_input(
            "Degree program (e.g., Master of Science in Computer Science)",
            required=True
        )

        self.config['EDUCATION_LOCATION'] = self.get_input(
            "University location (City, State)",
            default=f"{self.config.get('CITY', 'City')}, {self.config.get('STATE', 'State')}",
            required=False
        )

        self.config['EDUCATION_DATES'] = self.get_input(
            "Education dates (e.g., Jan 2020 -- May 2024)",
            required=False
        )

    def collect_professional_background(self):
        """Collect professional background."""
        self.print_section("Step 8: Professional Background")

        print(f"{Colors.CYAN}This information helps the AI generate better answers to application questions.{Colors.END}\n")

        self.config['YEARS_EXPERIENCE'] = self.get_input(
            "Years of professional experience",
            required=True,
            validator=lambda v: (v.isdigit() and 0 <= int(v) <= 50, "Must be a number between 0 and 50")
        )

        self.config['JOB_TITLE_CURRENT'] = self.get_input(
            "Current or most recent job title",
            required=True
        )

        self.config['TECH_STACK'] = self.get_input(
            "Your tech stack (comma-separated)",
            default="Python, JavaScript, React, Node.js",
            required=True
        )

        self.config['KEY_ACHIEVEMENT'] = self.get_input(
            "One key achievement or impact statement",
            default="Built scalable applications serving 100K+ users",
            required=False
        )

        self.config['SPECIALIZATIONS'] = self.get_input(
            "Your specializations or focus areas",
            default="Full-stack development, automation",
            required=False
        )

    def setup_resume_files(self):
        """Setup resume data files."""
        self.print_section("Step 9: Resume Data Setup")

        print(f"{Colors.CYAN}Resume and achievements files need to be created.{Colors.END}\n")

        # Check if base_resume.json exists
        base_resume = self.project_root / "base_resume.json"
        base_resume_example = self.project_root / "base_resume.json.example"

        if not base_resume.exists() and base_resume_example.exists():
            if self.get_yes_no("Create base_resume.json from example template?", default=True):
                shutil.copy(base_resume_example, base_resume)
                self.print_success(f"Created {base_resume}")
                self.print_warning("IMPORTANT: Edit base_resume.json with your actual work experience and projects!")

        # Check if achievements.txt exists
        achievements = self.project_root / "info" / "achievements.txt"
        achievements_example = self.project_root / "info" / "achievements.txt.example"

        # Create info directory if needed
        (self.project_root / "info").mkdir(exist_ok=True)

        if not achievements.exists() and achievements_example.exists():
            if self.get_yes_no("Create info/achievements.txt from example template?", default=True):
                shutil.copy(achievements_example, achievements)
                self.print_success(f"Created {achievements}")
                self.print_warning("IMPORTANT: Edit info/achievements.txt with your actual achievements!")

    def write_env_file(self):
        """Write configuration to .env file."""
        self.print_section("Step 10: Writing Configuration")

        try:
            # Read existing .env content
            env_lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r') as f:
                    env_lines = f.readlines()

            # Update values
            updated_lines = []
            keys_updated = set()

            for line in env_lines:
                line_stripped = line.strip()

                # Skip comments and empty lines
                if not line_stripped or line_stripped.startswith('#'):
                    updated_lines.append(line)
                    continue

                # Check if this line has a key we want to update
                if '=' in line_stripped:
                    key = line_stripped.split('=')[0].strip()
                    if key in self.config:
                        updated_lines.append(f"{key}={self.config[key]}\n")
                        keys_updated.add(key)
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)

            # Add any keys that weren't in the file
            for key, value in self.config.items():
                if key not in keys_updated:
                    updated_lines.append(f"{key}={value}\n")

            # Write updated content
            with open(self.env_file, 'w') as f:
                f.writelines(updated_lines)

            self.print_success(f"Configuration saved to {self.env_file}")
            return True

        except Exception as e:
            self.print_error(f"Failed to write .env file: {e}")
            return False

    def completion_message(self):
        """Display completion message with next steps."""
        self.print_header("SETUP COMPLETE!")

        print(f"{Colors.GREEN}✓ Configuration saved successfully{Colors.END}\n")

        print(f"{Colors.CYAN}{Colors.BOLD}Next Steps:{Colors.END}\n")

        print(f"{Colors.YELLOW}1. Edit your resume data:{Colors.END}")
        print(f"   Edit: {Colors.CYAN}base_resume.json{Colors.END} with your work experience and projects")
        print(f"   Edit: {Colors.CYAN}info/achievements.txt{Colors.END} with your achievements\n")

        print(f"{Colors.YELLOW}2. Verify your configuration:{Colors.END}")
        print(f"   Run: {Colors.CYAN}python config_validator.py{Colors.END}")
        print(f"   Or: {Colors.CYAN}python cli.py config-info{Colors.END}\n")

        print(f"{Colors.YELLOW}3. Set up MongoDB (if not already installed):{Colors.END}")
        print(f"   Install: {Colors.CYAN}brew install mongodb-community{Colors.END} (macOS)")
        print(f"   Start: {Colors.CYAN}brew services start mongodb-community{Colors.END}\n")

        print(f"{Colors.YELLOW}4. Install Python dependencies:{Colors.END}")
        print(f"   Run: {Colors.CYAN}pip install -r requirements.txt{Colors.END}\n")

        print(f"{Colors.YELLOW}5. Start using Job Agent:{Colors.END}")
        print(f"   Interactive mode: {Colors.CYAN}./job-agent interactive{Colors.END}")
        print(f"   Or: {Colors.CYAN}python cli.py interactive{Colors.END}\n")

        print(f"{Colors.CYAN}Documentation:{Colors.END}")
        print(f"   • README.md - Full documentation")
        print(f"   • .env.example - All configuration options")
        print(f"   • CLAUDE.md - Developer guide\n")

        print(f"{Colors.GREEN}Happy job hunting! 🚀{Colors.END}\n")

    def run(self):
        """Run the setup wizard."""
        try:
            self.welcome()
            self.check_system_dependencies()
            self.setup_env_file()
            self.collect_api_credentials()
            self.collect_personal_info()
            self.collect_address()
            self.collect_professional_profiles()
            self.collect_work_authorization()
            self.collect_education()
            self.collect_professional_background()
            self.setup_resume_files()

            if self.write_env_file():
                self.completion_message()
                return True
            else:
                self.print_error("Setup failed. Please check the errors above.")
                return False

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Setup cancelled by user.{Colors.END}")
            print(f"You can resume setup by running: {Colors.CYAN}python setup_wizard.py{Colors.END}\n")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error during setup: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    wizard = SetupWizard()
    success = wizard.run()
    sys.exit(0 if success else 1)
