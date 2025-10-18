"""
Configuration Validator for Job Agent
Validates required environment variables and provides helpful setup guidance.
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

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

# Required configuration fields with validation rules
REQUIRED_FIELDS = {
    # API Credentials
    'GEMINI_API_KEY': {
        'description': 'Google Gemini API Key',
        'required': True,
        'validation': lambda v: len(v) > 20 and v.startswith('AI'),
        'error_msg': 'Must be a valid Gemini API key (starts with "AI")',
        'help_url': 'https://aistudio.google.com/app/apikey'
    },

    # Personal Information
    'YOUR_NAME': {
        'description': 'Your Full Name',
        'required': True,
        'validation': lambda v: len(v) > 2 and ' ' in v.strip(),
        'error_msg': 'Must be your full name (first and last name)',
        'example': 'John Doe'
    },
    'FIRST_NAME': {
        'description': 'Your First Name',
        'required': True,
        'validation': lambda v: len(v) >= 2,
        'error_msg': 'Must be at least 2 characters',
        'example': 'John'
    },
    'LAST_NAME': {
        'description': 'Your Last Name',
        'required': True,
        'validation': lambda v: len(v) >= 2,
        'error_msg': 'Must be at least 2 characters',
        'example': 'Doe'
    },
    'YOUR_EMAIL': {
        'description': 'Your Email Address',
        'required': True,
        'validation': lambda v: '@' in v and '.' in v.split('@')[-1],
        'error_msg': 'Must be a valid email address',
        'example': 'your.email@example.com'
    },
    'YOUR_PHONE': {
        'description': 'Your Phone Number',
        'required': True,
        'validation': lambda v: len(v.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')) >= 10,
        'error_msg': 'Must be a valid phone number (at least 10 digits)',
        'example': '5551234567 or (555) 123-4567'
    },

    # Address
    'STREET_ADDRESS': {
        'description': 'Street Address',
        'required': True,
        'validation': lambda v: len(v) > 5,
        'error_msg': 'Must be a valid street address',
        'example': '123 Main Street'
    },
    'CITY': {
        'description': 'City',
        'required': True,
        'validation': lambda v: len(v) >= 2,
        'error_msg': 'Must be a valid city name',
        'example': 'New York'
    },
    'STATE': {
        'description': 'State/Province',
        'required': True,
        'validation': lambda v: len(v) >= 2,
        'error_msg': 'Must be a valid state or province',
        'example': 'New York or NY'
    },
    'ZIP_CODE': {
        'description': 'ZIP/Postal Code',
        'required': True,
        'validation': lambda v: len(v) >= 5,
        'error_msg': 'Must be a valid ZIP or postal code',
        'example': '10001'
    },
    'LOCATION': {
        'description': 'Location (as displayed on resume)',
        'required': True,
        'validation': lambda v: len(v) >= 3,
        'error_msg': 'Must be a valid location string',
        'example': 'New York, NY'
    },

    # Professional Profiles
    'YOUR_LINKEDIN_URL': {
        'description': 'LinkedIn Profile URL',
        'required': True,
        'validation': lambda v: 'linkedin.com' in v.lower(),
        'error_msg': 'Must be a valid LinkedIn URL',
        'example': 'https://linkedin.com/in/your-username'
    },
    'YOUR_GITHUB_URL': {
        'description': 'GitHub Profile URL',
        'required': True,
        'validation': lambda v: 'github.com' in v.lower(),
        'error_msg': 'Must be a valid GitHub URL',
        'example': 'https://github.com/your-username'
    },

    # Work Authorization
    'WORK_AUTHORIZED': {
        'description': 'Work Authorization Status',
        'required': True,
        'validation': lambda v: v.lower() in ['yes', 'no'],
        'error_msg': 'Must be "Yes" or "No"',
        'example': 'Yes'
    },
    'REQUIRE_SPONSORSHIP': {
        'description': 'Visa Sponsorship Required',
        'required': True,
        'validation': lambda v: v.lower() in ['yes', 'no', 'now', 'in the future'],
        'error_msg': 'Must be "Yes", "No", "Now", or "In the future"',
        'example': 'No'
    },

    # Professional Background
    'YEARS_EXPERIENCE': {
        'description': 'Years of Professional Experience',
        'required': True,
        'validation': lambda v: v.isdigit() and 0 <= int(v) <= 50,
        'error_msg': 'Must be a number between 0 and 50',
        'example': '3'
    },
    'JOB_TITLE_CURRENT': {
        'description': 'Current/Most Recent Job Title',
        'required': True,
        'validation': lambda v: len(v) >= 3,
        'error_msg': 'Must be a valid job title',
        'example': 'Software Engineer'
    },
    'TECH_STACK': {
        'description': 'Your Tech Stack (comma-separated)',
        'required': True,
        'validation': lambda v: ',' in v or len(v.split()) >= 2,
        'error_msg': 'Must list at least 2 technologies',
        'example': 'Python, JavaScript, React, Node.js'
    },
}

OPTIONAL_FIELDS = {
    'WEBSITE': 'Portfolio/Personal Website',
    'YOUR_LEETCODE_URL': 'LeetCode Profile URL',
    'LINKEDIN_LI_AT_COOKIE': 'LinkedIn Session Cookie (for scraping)',
    'JOBRIGHT_COOKIE_STRING': 'JobRight Cookie String (for scraping)',
    'MONGODB_CONNECTION_STRING': 'MongoDB Connection String',
    'DB_NAME': 'Database Name',
    'GEMINI_MODEL_NAME': 'Gemini Model Name',
    'KEY_ACHIEVEMENT': 'Key Achievement Statement',
    'SPECIALIZATIONS': 'Professional Specializations',
    'SOFT_SKILLS': 'Soft Skills',
    'CAREER_PASSION': 'Career Passion/Drive',
    'GENDER': 'Gender (for EEO forms)',
    'RACE_ETHNICITY': 'Race/Ethnicity (for EEO forms)',
    'VETERAN_STATUS': 'Veteran Status',
    'DISABILITY_STATUS': 'Disability Status',
}


class ConfigValidator:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.errors: List[Tuple[str, str]] = []
        self.warnings: List[Tuple[str, str]] = []
        self.passed: List[str] = []

    def print_color(self, text: str, color: str = Colors.WHITE, bold: bool = False):
        """Print colored text to console."""
        if bold:
            print(f"{Colors.BOLD}{color}{text}{Colors.END}")
        else:
            print(f"{color}{text}{Colors.END}")

    def validate_field(self, field_name: str, field_info: Dict) -> bool:
        """Validate a single configuration field."""
        # Import config to get actual loaded values
        import config as cfg
        value = str(getattr(cfg, field_name, '')).strip()

        # Check if required field is missing
        if field_info.get('required', False) and not value:
            error_msg = f"Missing required field: {field_name}"
            help_msg = f"  Description: {field_info['description']}"
            if 'example' in field_info:
                help_msg += f"\n  Example: {field_info['example']}"
            if 'help_url' in field_info:
                help_msg += f"\n  Get it here: {field_info['help_url']}"

            self.errors.append((error_msg, help_msg))
            return False

        # If not required and empty, skip validation
        if not value:
            return True

        # Run custom validation if provided
        if 'validation' in field_info:
            try:
                if not field_info['validation'](value):
                    error_msg = f"Invalid value for {field_name}"
                    help_msg = f"  Error: {field_info['error_msg']}"
                    if 'example' in field_info:
                        help_msg += f"\n  Example: {field_info['example']}"

                    self.errors.append((error_msg, help_msg))
                    return False
            except Exception as e:
                error_msg = f"Validation error for {field_name}"
                help_msg = f"  Error: {str(e)}"
                self.errors.append((error_msg, help_msg))
                return False

        self.passed.append(field_name)
        return True

    def validate_all(self) -> bool:
        """Validate all required configuration fields."""
        self.errors = []
        self.warnings = []
        self.passed = []

        # Validate required fields
        for field_name, field_info in REQUIRED_FIELDS.items():
            self.validate_field(field_name, field_info)

        # Check for optional but recommended fields
        import config as cfg
        for field_name, description in OPTIONAL_FIELDS.items():
            value = str(getattr(cfg, field_name, '')).strip()
            if not value and field_name in ['MONGODB_CONNECTION_STRING', 'DB_NAME']:
                self.warnings.append((
                    f"Optional field not set: {field_name}",
                    f"  Description: {description}\n  Default will be used"
                ))

        return len(self.errors) == 0

    def print_report(self):
        """Print a detailed validation report."""
        self.print_color("\n" + "="*80, Colors.CYAN, bold=True)
        self.print_color("  JOB AGENT - CONFIGURATION VALIDATION REPORT", Colors.CYAN, bold=True)
        self.print_color("="*80 + "\n", Colors.CYAN, bold=True)

        # Print passed validations
        if self.passed and self.verbose:
            self.print_color(f"✓ {len(self.passed)} fields validated successfully", Colors.GREEN, bold=True)
            if self.verbose:
                for field in self.passed[:5]:  # Show first 5
                    self.print_color(f"  ✓ {field}", Colors.GREEN)
                if len(self.passed) > 5:
                    self.print_color(f"  ... and {len(self.passed) - 5} more", Colors.GREEN)
            print()

        # Print warnings
        if self.warnings:
            self.print_color(f"⚠ {len(self.warnings)} Warnings:", Colors.YELLOW, bold=True)
            for warning, help_msg in self.warnings:
                self.print_color(f"  ⚠ {warning}", Colors.YELLOW)
                if help_msg:
                    print(f"{Colors.WHITE}{help_msg}{Colors.END}")
            print()

        # Print errors
        if self.errors:
            self.print_color(f"✗ {len(self.errors)} Errors Found:", Colors.RED, bold=True)
            for i, (error, help_msg) in enumerate(self.errors, 1):
                self.print_color(f"\n  {i}. {error}", Colors.RED, bold=True)
                if help_msg:
                    print(f"{Colors.WHITE}{help_msg}{Colors.END}")
            print()

            # Print instructions
            self.print_color("="*80, Colors.RED)
            self.print_color("  HOW TO FIX:", Colors.RED, bold=True)
            self.print_color("="*80, Colors.RED)
            print(f"{Colors.WHITE}")
            print("  1. Edit config.yaml and fill in your personal information:")
            print(f"     {Colors.CYAN}nano config.yaml{Colors.END}  (or use your preferred editor)")
            print()
            print("  2. Replace all REPLACE_WITH_* placeholders with your actual values")
            print()
            print("  3. Verify your configuration:")
            print(f"     {Colors.CYAN}./job-agent config{Colors.END}")
            print()
            print(f"{Colors.WHITE}  See config.yaml.example for field descriptions and examples.{Colors.END}")
            print()

            return False

        # Success message
        self.print_color("="*80, Colors.GREEN)
        self.print_color("  ✓ ALL VALIDATIONS PASSED!", Colors.GREEN, bold=True)
        self.print_color("="*80, Colors.GREEN)
        print(f"{Colors.WHITE}  Your configuration is ready to use.{Colors.END}\n")

        return True

    def get_missing_fields(self) -> List[str]:
        """Return list of missing required field names."""
        return [error for error, _ in self.errors]


def validate_configuration(verbose: bool = True, exit_on_error: bool = False) -> bool:
    """
    Main validation function.

    Args:
        verbose: Print detailed validation report
        exit_on_error: Exit the program if validation fails

    Returns:
        True if validation passed, False otherwise
    """
    validator = ConfigValidator(verbose=verbose)
    is_valid = validator.validate_all()

    if verbose or not is_valid:
        validator.print_report()

    if not is_valid and exit_on_error:
        sys.exit(1)

    return is_valid


def check_env_file_exists() -> bool:
    """Check if .env file exists."""
    project_root = Path(__file__).parent
    env_file = project_root / '.env'
    return env_file.exists()


def prompt_create_env_file():
    """Prompt user to create .env file from template."""
    project_root = Path(__file__).parent
    env_example = project_root / '.env.example'
    env_file = project_root / '.env'

    if not env_example.exists():
        print(f"{Colors.RED}Error: .env.example template not found!{Colors.END}")
        return False

    print(f"{Colors.YELLOW}No .env file found!{Colors.END}")
    print(f"\nWould you like to create one from .env.example? (y/n): ", end='')

    response = input().strip().lower()
    if response == 'y':
        try:
            import shutil
            shutil.copy(env_example, env_file)
            print(f"{Colors.GREEN}✓ Created .env file from template{Colors.END}")
            print(f"\n{Colors.CYAN}Next steps:{Colors.END}")
            print(f"  1. Edit .env and fill in your information")
            print(f"  2. Run: {Colors.CYAN}python cli.py setup{Colors.END} for guided setup")
            print(f"  3. Or run: {Colors.CYAN}python cli.py config-info{Colors.END} to verify")
            return True
        except Exception as e:
            print(f"{Colors.RED}Error creating .env file: {e}{Colors.END}")
            return False

    return False


if __name__ == '__main__':
    # When run directly, perform full validation
    print(f"{Colors.CYAN}Running configuration validation...{Colors.END}\n")

    # Check if .env exists
    if not check_env_file_exists():
        prompt_create_env_file()
        print()

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Validate
    is_valid = validate_configuration(verbose=True, exit_on_error=False)

    sys.exit(0 if is_valid else 1)
