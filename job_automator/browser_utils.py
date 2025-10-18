# job_automator/browser_utils.py
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
# Add other browser imports if needed (Firefox, Edge)

import config # Assuming config has needed paths/settings

logger = logging.getLogger(__name__)

INSTANCE = None # Singleton WebDriver instance (optional pattern)

def get_webdriver(browser_type="chrome", headless=False, force_new=False):
    """
    Initializes and returns a Selenium WebDriver instance.
    Uses webdriver-manager for driver management.
    Includes options to reduce detectability.
    Can optionally reuse a single instance.
    """
    global INSTANCE
    if INSTANCE and not force_new:
        logger.debug("Reusing existing WebDriver instance.")
        return INSTANCE

    logger.info(f"Initializing WebDriver: Type={browser_type}, Headless={headless}")
    driver = None
    try:
        if browser_type.lower() == "chrome":
            options = ChromeOptions()
            if headless: options.add_argument("--headless=new") # Use new headless mode
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"user-agent={config.DEFAULT_USER_AGENT}")

            # Use Chrome user data directory if configured (for session persistence)
            if config.CHROME_USER_DATA_DIR:
                logger.info(f"Using Chrome user data directory: {config.CHROME_USER_DATA_DIR}")
                options.add_argument(f"--user-data-dir={config.CHROME_USER_DATA_DIR}")

            # Anti-detection measures
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-blink-features=AutomationControlled')
            # Add arguments to disable logging/infobars
            options.add_argument("--log-level=3")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-logging")
            options.add_argument("--silent")

            # Use webdriver-manager
            try:
                logger.debug("Attempting to install/update ChromeDriver via webdriver-manager...")
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
                logger.info("Chrome WebDriver initialized successfully via webdriver-manager.")
            except Exception as e_wdm:
                 logger.error(f"webdriver-manager failed: {e_wdm}. Check network or permissions.", exc_info=True)
                 return None # Fail if manager fails

        # Add 'elif' for other browsers (firefox, edge) here if needed

        else:
            logger.error(f"Unsupported browser type requested: {browser_type}")
            return None

        # Configure driver settings
        driver.set_page_load_timeout(120) # Longer page load timeout
        driver.implicitly_wait(3) # Use short implicit wait, rely on explicit waits

        # Prevent webdriver detection by removing navigator.webdriver flag
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
              """
        })

        logger.info(f"{browser_type.capitalize()} WebDriver Ready.")
        INSTANCE = driver # Store as singleton if needed
        return driver

    except Exception as e:
        logger.error(f"Error initializing WebDriver for {browser_type}: {e}", exc_info=True)
        if driver:
            driver.quit()
        INSTANCE = None
        return None

def close_webdriver():
    """Closes the singleton WebDriver instance if it exists."""
    global INSTANCE
    if INSTANCE:
        logger.info("Closing WebDriver instance.")
        try:
            INSTANCE.quit()
        except Exception as e:
            logger.error(f"Error quitting WebDriver: {e}", exc_info=True)
        finally:
             INSTANCE = None
    else:
        logger.debug("No active WebDriver instance to close.")

# Example Usage (for testing)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
    logger.info("Testing WebDriver creation...")
    driver = get_webdriver(headless=True) # Test headless
    if driver:
        try:
            driver.get("https://httpbin.org/user-agent") # Check user agent
            ua_element = driver.find_element("tag name", "pre")
            logger.info(f"Detected User Agent: {ua_element.text}")
            driver.get("https://google.com")
            logger.info(f"Page title: {driver.title}")
        except Exception as e:
             logger.error(f"Error during WebDriver test: {e}")
        finally:
            close_webdriver()
    else:
        logger.error("Failed to create WebDriver.")

    logger.info("Testing reuse...")
    driver1 = get_webdriver(headless=True)
    driver2 = get_webdriver(headless=True) # Should reuse
    logger.info(f"driver1 is driver2: {driver1 is driver2}")
    close_webdriver()
    logger.info("Test complete.")