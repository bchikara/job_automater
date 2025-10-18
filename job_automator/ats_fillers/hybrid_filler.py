"""
Hybrid Filler - Intelligent routing between Browser-Use AI and traditional Selenium
"""

import logging
from typing import Optional
import config

# Try to import browser-use filler
try:
    from .browser_use_filler import BrowserUseFiller, BROWSER_USE_AVAILABLE
except ImportError:
    BROWSER_USE_AVAILABLE = False
    BrowserUseFiller = None

# Import traditional fillers
from .greenhouse_filler import GreenhouseFiller
from .workday_filler import WorkdayFiller  # If you have it
from .base_filler import BaseFiller


class HybridFiller:
    """
    Hybrid application filler that intelligently chooses between:
    1. Browser-Use AI agent (intelligent, works with any platform)
    2. Platform-specific Selenium fillers (reliable for known platforms)
    3. Generic Selenium filler (fallback)
    """

    def __init__(self, driver, job_data, user_profile, document_paths, credentials=None, ats_platform=None):
        self.driver = driver
        self.job_data = job_data
        self.user_profile = user_profile
        self.document_paths = document_paths
        self.credentials = credentials
        self.ats_platform = ats_platform
        self.logger = logging.getLogger(__name__)

        job_id = job_data.get('job_id', job_data.get('primary_identifier', 'unknown'))
        self.log_prefix = f"[HybridFiller - JobID: {job_id}] "

    def apply(self) -> str:
        """
        Intelligently apply to job using hybrid approach.
        Returns status string from config.
        """
        self.logger.info(f"{self.log_prefix}Starting hybrid application process...")
        self.logger.info(f"{self.log_prefix}Detected ATS Platform: {self.ats_platform or 'Unknown'}")

        # Strategy: Try methods in order of reliability for this platform
        strategies = self._determine_strategies()

        for strategy_name, strategy_func in strategies:
            self.logger.info(f"{self.log_prefix}Attempting strategy: {strategy_name}")

            try:
                result = strategy_func()

                # Check if it was successful
                if result == config.JOB_STATUS_APPLIED_SUCCESS:
                    self.logger.info(f"{self.log_prefix}✓ Success with {strategy_name}")
                    return result
                elif result in [config.JOB_STATUS_MANUAL_INTERVENTION_SUBMITTED,
                               config.JOB_STATUS_MANUAL_INTERVENTION_CLOSED_BY_USER]:
                    # Manual intervention results are final
                    self.logger.info(f"{self.log_prefix}Manual intervention: {result}")
                    return result
                else:
                    self.logger.warning(f"{self.log_prefix}✗ {strategy_name} failed with status: {result}")
                    # Continue to next strategy

            except Exception as e:
                self.logger.error(f"{self.log_prefix}✗ Exception in {strategy_name}: {e}", exc_info=True)
                # Continue to next strategy

        # All strategies failed
        self.logger.error(f"{self.log_prefix}All strategies failed")
        return config.JOB_STATUS_APP_FAILED_ATS

    def _determine_strategies(self):
        """
        Determine which strategies to try and in what order.
        Returns list of (strategy_name, strategy_function) tuples.
        """
        strategies = []

        # ONLY use Browser-Use (no Selenium fallback)
        self.logger.info(f"{self.log_prefix}Using Browser-Use AI ONLY (no fallback)")

        if BROWSER_USE_AVAILABLE:
            strategies.append(("Browser-Use AI", self._try_browser_use))
        else:
            self.logger.error(f"{self.log_prefix}Browser-Use not available! Cannot proceed.")

        # NO SELENIUM FALLBACK - Browser-Use only!
        # (Commented out as per user request)
        # strategies.append(("Selenium (fallback)", self._try_selenium_filler))

        return strategies

    def _try_browser_use(self) -> str:
        """Try Browser-Use AI agent"""
        if not BROWSER_USE_AVAILABLE:
            self.logger.warning(f"{self.log_prefix}Browser-Use not available")
            return config.JOB_STATUS_APP_FAILED_ATS

        try:
            self.logger.info(f"{self.log_prefix}Initializing Browser-Use AI agent...")

            # Create Browser-Use filler (it doesn't use self.driver)
            filler = BrowserUseFiller(
                job_data=self.job_data,
                user_profile=self.user_profile,
                document_paths=self.document_paths,
                credentials=self.credentials
            )

            # Run the agent
            result = filler.apply()
            return result

        except Exception as e:
            self.logger.error(f"{self.log_prefix}Browser-Use agent error: {e}", exc_info=True)
            return config.JOB_STATUS_APP_FAILED_ATS

    def _try_selenium_filler(self) -> str:
        """Try platform-specific or generic Selenium filler"""
        try:
            # Choose appropriate filler based on ATS platform
            if self.ats_platform:
                platform_lower = self.ats_platform.lower()

                if 'greenhouse' in platform_lower:
                    self.logger.info(f"{self.log_prefix}Using Greenhouse Selenium filler")
                    filler = GreenhouseFiller(
                        driver=self.driver,
                        job_data=self.job_data,
                        user_profile=self.user_profile,
                        document_paths=self.document_paths,
                        credentials=self.credentials
                    )
                elif 'workday' in platform_lower:
                    self.logger.info(f"{self.log_prefix}Using Workday Selenium filler")
                    # Assuming you have WorkdayFiller
                    try:
                        filler = WorkdayFiller(
                            driver=self.driver,
                            job_data=self.job_data,
                            user_profile=self.user_profile,
                            document_paths=self.document_paths,
                            credentials=self.credentials
                        )
                    except (ImportError, NameError):
                        self.logger.warning(f"{self.log_prefix}WorkdayFiller not available, using Greenhouse as fallback")
                        filler = GreenhouseFiller(
                            driver=self.driver,
                            job_data=self.job_data,
                            user_profile=self.user_profile,
                            document_paths=self.document_paths,
                            credentials=self.credentials
                        )
                else:
                    # Unknown platform, use generic filler (e.g., Greenhouse as template)
                    self.logger.info(f"{self.log_prefix}Using generic Selenium filler for {self.ats_platform}")
                    filler = GreenhouseFiller(
                        driver=self.driver,
                        job_data=self.job_data,
                        user_profile=self.user_profile,
                        document_paths=self.document_paths,
                        credentials=self.credentials
                    )
            else:
                # No ATS detected, use default
                self.logger.info(f"{self.log_prefix}No ATS detected, using default Greenhouse filler")
                filler = GreenhouseFiller(
                    driver=self.driver,
                    job_data=self.job_data,
                    user_profile=self.user_profile,
                    document_paths=self.document_paths,
                    credentials=self.credentials
                )

            # Run the filler
            result = filler.apply()
            return result

        except Exception as e:
            self.logger.error(f"{self.log_prefix}Selenium filler error: {e}", exc_info=True)
            return config.JOB_STATUS_APP_FAILED_ATS


# Export for use in automator
__all__ = ['HybridFiller', 'BROWSER_USE_AVAILABLE']
