# job_automator/automator_main.py
import logging
import os
import sys
import time
import json
import shutil
from pathlib import Path
import datetime

# Ensure project root is in path for sibling imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path: sys.path.append(str(PROJECT_ROOT))

# Project imports
import config
import database
from utils import create_dir_if_not_exists # Util for creating dirs if needed by move logic
# Automator specific imports
from . import ats_identifier
from . import browser_utils
# Import base filler and specific fillers
from .ats_fillers import base_filler # Import base for ApplicationError and type hinting
from .ats_fillers import greenhouse_filler
from .ats_fillers import workday_filler
# from .ats_fillers import lever_filler # Add more as implemented

logger = logging.getLogger(__name__)

# Map platform names (lowercase) from ats_identifier to filler classes
ATS_FILLER_MAP = {
    "greenhouse": greenhouse_filler.GreenhouseFiller,
    "workday": workday_filler.WorkdayFiller,
    # "lever": lever_filler.LeverFiller,
    # Add mappings here...
}

def _move_processed_folder(source_dir: str | Path, dest_base_dir: str | Path):
    """Moves the job document folder to the appropriate processed directory."""
    source_path = Path(source_dir)
    dest_base_path = Path(dest_base_dir)
    log_prefix = f"[{source_path.name}] " # Use folder name for context

    if not source_path.is_dir():
        logger.error(f"{log_prefix}Cannot move folder: Source directory '{source_path}' not found or invalid.")
        return None # Return None if source doesn't exist

    # Ensure destination base exists (should be done by caller, but double check)
    dest_base_path.mkdir(parents=True, exist_ok=True)
    final_dest_path = dest_base_path / source_path.name # Keep original unique folder name

    try:
        # Handle existing destination folder
        if final_dest_path.exists():
             logger.warning(f"{log_prefix}Destination path '{final_dest_path}' already exists. Removing existing before move.")
             shutil.rmtree(final_dest_path)

        logger.info(f"{log_prefix}Moving processed folder from '{source_path}' to '{final_dest_path}'")
        shutil.move(str(source_path), str(final_dest_path))
        logger.info(f"{log_prefix}Folder moved successfully.")
        return str(final_dest_path) # Return the new path string
    except Exception as e:
        logger.error(f"{log_prefix}Error moving folder '{source_path.name}' to '{final_dest_path}': {e}", exc_info=True)
        # Folder remains in source location on error
        return None


def attempt_application(job_data: dict, processed_paths: dict) -> str:
    """
    Main orchestrator for attempting a single job application.
    Handles Easy Apply, ATS identification, running fillers, status updates, folder moves.

    Args:
        job_data: Job document from MongoDB.
        processed_paths: Dict containing paths to 'success', 'failure', 'easy_apply' dirs.

    Returns:
        str: The final status string set for the job (e.g., config.JOB_STATUS_APPLIED_SUCCESS).
    """
    primary_id = job_data.get('primary_identifier')
    application_url = job_data.get('application_url')
    source_doc_dir = job_data.get('job_specific_output_dir') # Dir where PDFs are
    log_prefix = f"[{primary_id}] "
    final_status = config.JOB_STATUS_ERROR_UNKNOWN
    final_folder_path = source_doc_dir
    status_reason = "Application process initiated."

    # --- Pre-checks ---
    if not primary_id: logger.error("Attempt rejected: Missing primary_identifier."); return config.JOB_STATUS_ERROR_UNKNOWN
    if not source_doc_dir or not Path(source_doc_dir).is_dir():
        logger.error(f"{log_prefix}Attempt rejected: Source dir missing/invalid: '{source_doc_dir}'.")
        database.update_job_status(primary_id, config.JOB_STATUS_ERROR_UNKNOWN, "Source doc dir missing for app phase.")
        return config.JOB_STATUS_ERROR_UNKNOWN

    # --- 1. Handle "Easy Apply" ---
    if not application_url:
        logger.info(f"{log_prefix}Identified as 'Easy Apply'. Moving folder.")
        moved_path = _move_processed_folder(source_doc_dir, processed_paths["easy_apply"])
        if moved_path:
            final_status = "easy_apply_processed"; status_reason = "Categorized as Easy Apply"
            final_folder_path = moved_path
        else:
            final_status = config.JOB_STATUS_ERROR_UNKNOWN; status_reason = "Failed to move Easy Apply folder"
        database.update_job_data(primary_id, {'status': final_status, 'status_reason': status_reason, 'job_specific_output_dir': final_folder_path})
        return final_status

    # --- 2. Handle ATS Application ---
    logger.info(f"{log_prefix}Attempting ATS application for URL: {application_url}")
    database.update_job_status(primary_id, config.JOB_STATUS_APP_IN_PROGRESS, "Identifying ATS platform.")
    ats_platform = ats_identifier.identify_ats_platform(application_url)

    if not ats_platform:
        logger.warning(f"{log_prefix}Could not identify ATS platform. Moving to failure.")
        final_status = config.JOB_STATUS_APP_FAILED_ATS; status_reason = "ATS platform not identified"
        moved_path = _move_processed_folder(source_doc_dir, processed_paths["failure"])
        final_folder_path = moved_path
        database.update_job_data(primary_id, {'status': final_status, 'status_reason': status_reason, 'job_specific_output_dir': final_folder_path})
        return final_status

    FillerClass = ATS_FILLER_MAP.get(ats_platform)
    if not FillerClass:
        logger.warning(f"{log_prefix}No ATS filler implemented for '{ats_platform}'. Moving to failure.")
        final_status = config.JOB_STATUS_APP_FAILED_ATS; status_reason = f"No filler for {ats_platform}"
        moved_path = _move_processed_folder(source_doc_dir, processed_paths["failure"])
        final_folder_path = moved_path
        database.update_job_data(primary_id, {'status': final_status, 'status_reason': status_reason, 'job_specific_output_dir': final_folder_path})
        return final_status

    # --- 3. Prepare User Profile & Docs ---
    # TODO: Load user_profile more dynamically (e.g., parse base_resume.json)
    user_profile = { "full_name": config.YOUR_NAME, "email": config.YOUR_EMAIL, "phone": config.YOUR_PHONE,
                     "linkedin": config.YOUR_LINKEDIN_URL, "github": config.YOUR_GITHUB_URL, 
                     "website":config.WEBSITE,
                     "first_name":config.FIRST_NAME,"last_name":config.LAST_NAME,"location":config.LOCATION }
    document_paths = { "resume": job_data.get("resume_pdf_path"), "cover_letter": job_data.get("cover_letter_pdf_path") }
    if not document_paths.get("resume") or not Path(document_paths["resume"]).is_file():
        logger.error(f"{log_prefix}Cannot apply: Resume PDF missing or invalid path: {document_paths.get('resume')}")
        final_status = config.JOB_STATUS_ERROR_UNKNOWN; status_reason = "Resume PDF missing/invalid for application"
        moved_path = _move_processed_folder(source_doc_dir, processed_paths["failure"])
        final_folder_path = moved_path
        database.update_job_data(primary_id, {'status': final_status, 'status_reason': status_reason, 'job_specific_output_dir': final_folder_path})
        return final_status

    # --- 4. Execute ATS Filling ---
    driver = None
    application_result_status = config.JOB_STATUS_APP_FAILED_ATS # Default failure
    error_details = "Process started but did not complete successfully."
    try:
        database.update_job_status(primary_id, config.JOB_STATUS_APP_IN_PROGRESS, f"Initializing {ats_platform} filler.")
        driver = browser_utils.get_webdriver() # Uses defaults from browser_utils
        if not driver: raise base_filler.ApplicationError("Failed to initialize WebDriver.", config.JOB_STATUS_ERROR_UNKNOWN)

        # TODO: Fetch credentials if FillerClass.requires_login() is True
        credentials = None

        logger.info(f"{log_prefix}Instantiating and running {FillerClass.__name__}...")
        filler = FillerClass(driver, job_data, user_profile, document_paths, credentials)
        application_result_status = filler.apply() # This should return a JOB_STATUS_* string

        # If apply() finished without raising ApplicationError, get reason based on status
        if application_result_status == config.JOB_STATUS_APPLIED_SUCCESS:
            error_details = "" # Success
            status_reason = f"Application submitted successfully via {ats_platform}."
        else:
            # Application finished but reported failure internally
             error_details = f"Filler completed with non-success status: {application_result_status}"
             status_reason = error_details

    except base_filler.ApplicationError as app_err:
        logger.error(f"{log_prefix}Application Error ({ats_platform}): {app_err.message}")
        application_result_status = app_err.status
        error_details = f"ApplicationError: {app_err.message[:500]}"
        status_reason = error_details
    except Exception as e:
        logger.error(f"{log_prefix}Unexpected Exception during ATS filling ({ats_platform}): {e}", exc_info=True)
        application_result_status = config.JOB_STATUS_APP_FAILED_ATS # Generic failure
        error_details = f"Unexpected Exception: {str(e)[:500]}"
        status_reason = error_details
    finally:
        browser_utils.close_webdriver() # Ensure browser closes

    # --- 5. Handle Final Outcome ---
    final_status = application_result_status
    dest_dir_path = processed_paths["success"] if final_status == config.JOB_STATUS_APPLIED_SUCCESS else processed_paths["failure"]
    moved_path = _move_processed_folder(source_doc_dir, dest_dir_path)
    final_folder_path = moved_path or source_doc_dir # Track final location

    # Final DB update
    db_update = {'status': final_status, 'status_reason': status_reason}
    if final_folder_path and final_folder_path != source_doc_dir : db_update['job_specific_output_dir'] = final_folder_path
    if final_status == config.JOB_STATUS_APPLIED_SUCCESS: db_update['submitted_at'] = datetime.datetime.now(datetime.timezone.utc)
    if error_details and final_status != config.JOB_STATUS_APPLIED_SUCCESS: db_update['error_log'] = error_details
    db_update['last_attempted_at'] = datetime.datetime.now(datetime.timezone.utc)

    database.update_job_data(primary_id, db_update)
    logger.info(f"{log_prefix}Final application status: {final_status}. Folder location: {final_folder_path}")

    return final_status