"""
Browser-Use Session Manager - Maintains a single persistent browser session

IMPORTANT: Browser-use with the SAME user_data_dir automatically reuses the same browser instance.
This manager ensures we use a consistent profile directory and initialized LLM.
"""
import logging
from pathlib import Path
from typing import Optional

try:
    from browser_use import Agent
    from browser_use.llm.google.chat import ChatGoogle
    from browser_use.browser.profile import BrowserProfile
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Agent = None
    ChatGoogle = None
    BrowserProfile = None

import config


class BrowserUseSessionManager:
    """
    Singleton manager for browser-use sessions.

    KEY INSIGHT: Browser-use with the same user_data_dir in BrowserProfile
    automatically reuses the same Playwright browser instance across multiple Agent creations.

    This manager provides:
    1. A singleton LLM instance (no need to recreate for each job)
    2. A singleton BrowserProfile (ensures same user_data_dir = same browser)
    3. Session tracking for logging
    """

    _instance: Optional['BrowserUseSessionManager'] = None

    def __init__(self):
        """Private constructor - use get_instance() instead"""
        if not BROWSER_USE_AVAILABLE:
            raise ImportError("browser-use library is required")

        self.logger = logging.getLogger(__name__)
        self.profile: Optional[BrowserProfile] = None
        self.llm: Optional[ChatGoogle] = None

        # Session state
        self._initialized = False
        self._session_count = 0

        self.logger.info("BrowserUseSessionManager created (singleton)")

    @classmethod
    def get_instance(cls) -> 'BrowserUseSessionManager':
        """Get or create the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self) -> bool:
        """
        Initialize the LLM and browser profile once.
        This is lightweight - actual browser creation happens on first Agent.run()
        """
        if self._initialized:
            self.logger.info("Session manager already initialized")
            return True

        try:
            self.logger.info("Initializing browser session manager...")

            # Check API key
            if not config.GEMINI_API_KEY:
                self.logger.error("GEMINI_API_KEY not configured!")
                return False

            # Initialize LLM once (shared across all agents)
            self.logger.info("Initializing Gemini LLM (gemini-2.5-flash-lite)...")
            self.llm = ChatGoogle(
                model="gemini-2.5-flash-lite",
                temperature=0.3,
                api_key=config.GEMINI_API_KEY
            )
            self.logger.info("✓ LLM initialized")

            # Create persistent profile directory
            # Use config value if set, otherwise default to .job_agent_browser_profile
            if config.CHROME_USER_DATA_DIR:
                app_profile_dir = Path(config.CHROME_USER_DATA_DIR)
                self.logger.info(f"Using Chrome user data directory from config: {app_profile_dir}")
                self.logger.warning("⚠️  Using main Chrome profile - CLOSE ALL Chrome windows before running job-agent!")
                self.logger.warning("⚠️  If browser doesn't open, Chrome may be locked by another instance.")
            else:
                app_profile_dir = Path.home() / '.job_agent_browser_profile'
                self.logger.info(f"Using default profile directory: {app_profile_dir}")

            app_profile_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"✓ Profile directory ready: {app_profile_dir}")
            self.logger.info(f"✓ Browser will open in VISIBLE mode (headless=False)")

            # Create browser profile (shared across all agents)
            # Using the SAME user_data_dir means browser-use reuses the same browser!
            self.profile = BrowserProfile(
                user_data_dir=str(app_profile_dir),
                headless=False,
                disable_security=False,
                extra_chromium_args=[
                    '--disable-blink-features=AutomationControlled',
                    '--window-size=1920,1080',
                    '--start-maximized',
                ]
            )
            self.logger.info("✓ Browser profile created")

            self._initialized = True
            self.logger.info("✅ Session manager initialized (browser will start on first agent.run())")

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize session manager: {e}", exc_info=True)
            return False

    def create_agent(self, task: str, available_file_paths: list = None) -> Optional[Agent]:
        """
        Create a new Agent instance.

        IMPORTANT: All agents created with the SAME BrowserProfile (same user_data_dir)
        will automatically reuse the same browser instance. This is built into browser-use!

        Args:
            task: The task description for the agent
            available_file_paths: List of file paths the agent can access for uploads

        Returns:
            Agent instance, or None if creation failed
        """
        if not self._initialized:
            self.logger.info("Manager not initialized, initializing now...")
            if not self.initialize():
                return None

        try:
            self._session_count += 1
            session_id = self._session_count

            if session_id == 1:
                self.logger.info(f"[Session #{session_id}] Creating first agent (will initialize browser on first run)...")
            else:
                self.logger.info(f"[Session #{session_id}] Creating agent (will REUSE existing browser)...")

            # Create agent - browser-use handles browser reuse automatically!
            agent = Agent(
                task=task,
                llm=self.llm,  # Reused LLM
                browser_profile=self.profile,  # Same profile = same browser!
                use_vision=True,
                max_failures=5,
                max_actions_per_step=10,
                available_file_paths=available_file_paths or [],
                llm_timeout=90,
            )

            self.logger.info(f"[Session #{session_id}] ✓ Agent created")
            return agent

        except Exception as e:
            self.logger.error(f"Failed to create agent: {e}", exc_info=True)
            return None

    def reset(self):
        """Reset the manager state (useful for testing)"""
        self._initialized = False
        self._session_count = 0
        self.profile = None
        self.llm = None
        self.logger.info("Session manager reset")

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance"""
        if cls._instance:
            cls._instance.reset()
            cls._instance = None
            logging.getLogger(__name__).info("Singleton instance reset")


# Export
__all__ = ['BrowserUseSessionManager', 'BROWSER_USE_AVAILABLE']
