import re
import logging
from html import unescape
from bs4 import BeautifulSoup # For HTML decoding

# Configure logging for this utility module if needed, or rely on main script's config
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - UTILS - %(levelname)s - %(message)s')

def escape_latex(text):
    """
    Applies basic escaping for common LaTeX special characters.
    Handles potential None input.
    """
    if text is None:
        return '' # Return empty string for None input
    if not isinstance(text, str):
        try:
            text = str(text) # Try converting non-strings
        except Exception:
             logging.warning(f"Could not convert value to string for escaping: {type(text)}", exc_info=True)
             return '' # Return empty if conversion fails

    # logging.debug(f"Attempting to escape text starting with: {text[:50]}...") # Log input
    # Order matters, especially for backslash
    conv = {
        # Must be first!
        '\\': r'\textbackslash{}',
        # Other special characters
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        # Potentially problematic characters in text mode
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    # Use regex to perform replacements safely
    # This pattern finds any character in the conv keys
    regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key=len, reverse=True)))
    escaped_text = regex.sub(lambda match: conv[match.group(0)], text)
    # if escaped_text != text:
    #     logging.debug(f"Escaped text result starts with: {escaped_text[:50]}...") # Log output if changed
    # else:
    #      logging.debug("No escaping applied to text.")
    return escaped_text

def decode_html_to_text(html_content):
    """
    Decodes HTML entities and strips HTML tags to get plain text.
    Handles None input.
    """
    if not html_content:
        return ""
    try:
        # Use BeautifulSoup to parse HTML and get text
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True) # Use newline as separator, strip whitespace
        # Decode HTML entities like &amp;, &lt;, etc.
        text = unescape(text)
        return text
    except Exception as e:
        logging.error(f"Error decoding HTML: {e}", exc_info=True)
        # Fallback: return the original content if decoding fails badly
        # Or return a specific error message if preferred
        return str(html_content)


# Add any other utility functions here if needed
