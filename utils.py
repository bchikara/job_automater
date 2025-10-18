# utils.py
import re
import logging
import os
import sys
from html import unescape
from pathlib import Path
from bs4 import BeautifulSoup # Preferred for HTML decoding

# --- Path Configuration & Project Root Determination ---
# Try to determine project root dynamically. Assumes utils.py might be nested.
try:
    _current_file_path = Path(__file__).resolve()
    PROJECT_ROOT = _current_file_path.parent # Default: assume utils.py is in root
    # Search upwards for a root marker
    for i in range(4):
        if (PROJECT_ROOT / 'main.py').exists() or (PROJECT_ROOT / '.git').exists() or (PROJECT_ROOT / 'pyproject.toml').exists():
            break # Found root
        if PROJECT_ROOT.parent == PROJECT_ROOT:
            break # Reached filesystem root
        PROJECT_ROOT = PROJECT_ROOT.parent
    else: # If loop finished without finding marker
        PROJECT_ROOT = Path(__file__).resolve().parent # Fallback
        print(f"WARN [utils.py]: Could not find project root marker. Using directory of utils.py: {PROJECT_ROOT}")
except NameError:
    PROJECT_ROOT = Path.cwd() # Fallback if __file__ is not defined
    print(f"WARN [utils.py]: __file__ not defined. Using current working directory as root: {PROJECT_ROOT}")

# Template directory relative to project root
TEMPLATE_DIR = PROJECT_ROOT / 'document_generator' / 'templates'


# --- Logging Setup Function ---
def setup_logging(name="job_automator", log_level_str="INFO", log_dir=None, log_filename="app.log", console_output=False):
    """
    Configures root logger with console and file handlers.
    Also suppresses verbose output from third-party libraries.

    Args:
        name: Logger name
        log_level_str: Log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        log_filename: Name of log file
        console_output: If False, suppress all console logging (only log to file)
    """
    log_level_enum = getattr(logging, log_level_str.upper(), logging.INFO)

    root_logger = logging.getLogger() # Get the root logger

    # Clear existing handlers (important if called multiple times or after basicConfig)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.setLevel(log_level_enum) # Set level on the root logger

    # Console Handler - Only add if console_output is True
    if console_output:
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        ch.setLevel(log_level_enum)
        root_logger.addHandler(ch)

    # File Handler (if directory provided) - Always log to file
    if log_dir:
        log_dir_path = Path(log_dir)
        try:
            log_dir_path.mkdir(parents=True, exist_ok=True)
            log_file_path = log_dir_path / log_filename
            # File handler uses detailed format
            file_formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s",
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            fh = logging.FileHandler(log_file_path, encoding='utf-8')
            fh.setFormatter(file_formatter)
            fh.setLevel(log_level_enum) # Set level on handler
            root_logger.addHandler(fh)
        except Exception as e:
            # Only print error if console output is enabled
            if console_output:
                print(f"Failed to setup file logging to {log_dir}: {e}")

    # Suppress verbose third-party library logging
    _suppress_third_party_logs()

    # Modules should get their own logger via: logger = logging.getLogger(__name__)


def _suppress_third_party_logs():
    """Suppress verbose logging from third-party libraries"""
    # Google AI/Gemini related
    logging.getLogger('google').setLevel(logging.ERROR)
    logging.getLogger('google.ai').setLevel(logging.ERROR)
    logging.getLogger('google.generativeai').setLevel(logging.ERROR)
    logging.getLogger('google.api_core').setLevel(logging.ERROR)
    logging.getLogger('google.auth').setLevel(logging.ERROR)

    # Selenium/WebDriver
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # Other common verbose libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    # Suppress absl warnings (from Google libraries)
    try:
        import absl.logging
        absl.logging.set_verbosity(absl.logging.ERROR)
        absl.logging.set_stderrthreshold(absl.logging.ERROR)
    except ImportError:
        pass


# --- File System Utilities ---
def create_dir_if_not_exists(directory_path):
    """Creates a directory if it does not already exist."""
    logger = logging.getLogger(__name__)
    path = Path(directory_path)
    if not path.exists():
        logger.info(f"Directory not found. Creating: {path}")
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Error creating directory {path}: {e}", exc_info=True)
            raise
    # else: logger.debug(f"Directory already exists: {path}")


def sanitize_filename_component(name_part, max_length=50):
    """Sanitizes a string to be suitable as part of a filename."""
    logger = logging.getLogger(__name__)
    if name_part is None: name_part = ""

    try:
        name_part_str = str(name_part).strip()
        if not name_part_str: return "unknown"
        # Allow alphanumeric, underscore, hyphen. Replace others with underscore.
        sanitized = re.sub(r'[^A-Za-z0-9_\-]+', '_', name_part_str)
        # Condense multiple underscores/hyphens
        sanitized = re.sub(r'[_]+', '_', sanitized)
        sanitized = re.sub(r'[-]+', '-', sanitized)
        # Remove leading/trailing separators
        sanitized = sanitized.strip('_-')
        # Truncate and strip again
        sanitized = sanitized[:max_length].strip('_-')
        return sanitized if sanitized else "unknown"
    except Exception as e:
        logger.error(f"Error sanitizing component '{name_part}': {e}", exc_info=True)
        return "error_sanitizing"


# --- Text Processing Utilities ---
def escape_latex(text):
    """Escapes special LaTeX characters. Handles None input."""
    logger = logging.getLogger(__name__)
    if text is None: return ''
    if not isinstance(text, str):
        try: text = str(text)
        except Exception:
            logger.warning(f"Could not convert {type(text)} to string for LaTeX escape.", exc_info=True)
            return ''
    # LaTeX character escape mapping
    conv = {
        '\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
        '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}', '"': r"''", '“': r"``", '”': r"''",
        '‘': r"`", '’': r"'", '<': r'\textless{}', '>': r'\textgreater{}',
        '|': r'\textbar{}', '—': r'---', '–': r'--', '…': r'\dots{}',
    }
    pattern = '|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key=len, reverse=True))
    regex = re.compile(pattern)
    return regex.sub(lambda match: conv[match.group(0)], text)


def decode_html_to_text(html_content):
    """Decodes HTML using BeautifulSoup for better results."""
    logger = logging.getLogger(__name__)
    if not html_content: return ""
    try:
        # Basic structure preservation: Add newlines for block-level elements
        temp_html = str(html_content)
        temp_html = re.sub(r'<br\s*/?>', '\n', temp_html, flags=re.I)
        for tag in ['p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            temp_html = re.sub(rf'</{tag}\s*>', f'</{tag}>\n', temp_html, flags=re.I)

        soup = BeautifulSoup(temp_html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True) # Use space separator initially, then clean
        text = unescape(text) # Decode entities like &amp;

        # Clean up whitespace
        text = re.sub(r'[ \t]+', ' ', text) # Consolidate spaces/tabs
        text = re.sub(r'\n\s*\n', '\n\n', text) # Limit consecutive newlines
        return text.strip()
    except Exception as e:
        logger.error(f"Error decoding HTML: {e}", exc_info=True)
        # Fallback: basic unescape and regex tag removal
        try:
            fallback_text = unescape(str(html_content))
            fallback_text = re.sub(r'<[^>]+>', ' ', fallback_text)
            return re.sub(r'\s+', ' ', fallback_text).strip()
        except Exception:
            return str(html_content) # Absolute fallback


def load_template(template_filename):
    """Loads a template file from the configured templates directory."""
    logger = logging.getLogger(__name__)
    if not TEMPLATE_DIR.is_dir():
        logger.error(f"Template directory does not exist: {TEMPLATE_DIR}")
        raise FileNotFoundError(f"Template directory missing: {TEMPLATE_DIR}")

    filepath = TEMPLATE_DIR / template_filename
    logger.info(f"Loading template: {filepath}")
    if not filepath.is_file():
        logger.error(f"Template file not found: {filepath}")
        raise FileNotFoundError(f"Template file missing: {filepath}. Expected in {TEMPLATE_DIR}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Could not read template file {filepath}: {e}", exc_info=True)
        raise