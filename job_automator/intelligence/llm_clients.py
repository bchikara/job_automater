# job_automator/intelligence/llm_clients.py
import logging
import sys
import os
from pathlib import Path

# Ensure project root is in path for config import
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    import config
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import required libraries for llm_clients.py: {e}. Install langchain-google-genai.", file=sys.stderr)
    # Cannot use logger here as it might not be configured
    sys.exit(1)


logger = logging.getLogger(__name__)

# --- Gemini Client Setup ---
GEMINI_LLM = None
LLM_INIT_STATUS = "Not Initialized"

def initialize_llm():
    """Initializes the Gemini LLM client if not already done."""
    global GEMINI_LLM, LLM_INIT_STATUS
    if GEMINI_LLM:
        logger.debug("LLM client already initialized.")
        return # Already initialized

    logger.info("Initializing LLM client (Gemini)...")
    try:
        if not config.GEMINI_API_KEY:
            LLM_INIT_STATUS = "API Key Missing"
            logger.error("Cannot initialize Gemini LLM: GEMINI_API_KEY not found in config.")
            return

        # Consider adding more generation config options if needed
        GEMINI_LLM = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL_NAME,
            temperature=0.3, # Lower temp for more predictable results
            # Add safety_settings matching your general use case if desired
            # safety_settings=[...],
            google_api_key=config.GEMINI_API_KEY # Explicitly pass key if needed
        )
        LLM_INIT_STATUS = "Success"
        logger.info(f"ChatGoogleGenerativeAI initialized successfully with model: {config.GEMINI_MODEL_NAME}")

    except Exception as e:
        LLM_INIT_STATUS = f"Error: {e}"
        logger.error(f"Failed to initialize Gemini LLM {config.GEMINI_MODEL_NAME}: {e}", exc_info=True)
        GEMINI_LLM = None # Ensure it's None on failure

def get_llm_client():
    """Returns the initialized LLM client instance, initializing if needed."""
    # Attempt initialization only if not previously attempted or if status indicates readiness
    if not GEMINI_LLM and LLM_INIT_STATUS in ["Not Initialized"]:
        initialize_llm()

    if not GEMINI_LLM:
         # Log warning only if initialization failed, not if API key was missing initially
         if LLM_INIT_STATUS != "API Key Missing":
             logger.warning(f"LLM client could not be obtained. Status: {LLM_INIT_STATUS}")
         else:
             logger.debug("LLM client not available due to missing API Key.")

    return GEMINI_LLM

# Example Usage / Test
if __name__ == '__main__':
     # Need to set up basic logging if running standalone
     log_format = '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
     logging.basicConfig(level=logging.INFO, format=log_format)

     logger.info("Testing LLM client initialization...")
     llm = get_llm_client()
     if llm:
         logger.info("LLM Client obtained successfully.")
         # Example basic invocation (requires a valid API key set in config/.env)
         try:
             # Ensure config is loaded if run standalone
             from dotenv import load_dotenv
             env_path = PROJECT_ROOT / '.env'
             if env_path.exists(): load_dotenv(dotenv_path=env_path)
             # Reload config value if it wasn't picked up initially
             if not config.GEMINI_API_KEY: config.GEMINI_API_KEY=os.getenv('GEMINI_API_KEY')

             if config.GEMINI_API_KEY:
                 logger.info("Attempting test LLM invocation...")
                 response = llm.invoke("Explain what an ATS is in one brief sentence.")
                 logger.info(f"LLM Test Response: {getattr(response, 'content', 'No content found')}")
             else:
                  logger.warning("Skipping LLM test invocation: API Key missing.")
         except Exception as e:
             logger.error(f"LLM test invocation failed: {e}", exc_info=True)
     else:
         logger.error(f"Failed to obtain LLM Client. Status: {LLM_INIT_STATUS}")