# main.py
import os
import sys
import logging
import time
import traceback
from datetime import datetime, timezone
import argparse
from pathlib import Path
import shutil # Needed if you add folder moving logic later

# --- Setup Python Path ---
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- Import Custom Modules ---
# Basic config needed early for logging setup if possible

import config

# Setup logging using config values
try:
    # Import setup_logging *after* basic path/config setup
    from utils import setup_logging, create_dir_if_not_exists, sanitize_filename_component
    log_dir_path = PROJECT_ROOT / config.LOG_DIR_NAME
    # Configure root logger based on config
    setup_logging(name="job_automator", log_level_str=config.LOG_LEVEL, log_dir=log_dir_path)
    logger = logging.getLogger("job_automator.main") # Get logger instance after setup
    logger.info(f"--- main.py execution started (Log Level: {config.LOG_LEVEL}) ---")
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"Logging to directory: {log_dir_path}")
except Exception as log_setup_e:
    # Fallback basic logging if setup fails
    logging.basicConfig(level=config.LOG_LEVEL, format='%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger("job_automator.main")
    logger.error(f"Failed to setup file logging: {log_setup_e}", exc_info=True)
    logger.warning("Continuing with console logging only.")

# --- Import Remaining Custom Modules ---
try:
    logger.debug("Importing remaining project modules...")
    import database
    from scrapers import linkedin_scraper, jobright_scraper
    from resume_tailor import tailor as resume_tailor_module
    from document_generator import generator as document_generator_module # Import the module itself
    # Import job automator main function (ensure this file exists and is importable)
    from job_automator import automator_main
    # utils already imported for setup_logging etc.
    logger.info("Project modules imported successfully.")
except ImportError as e:
    logger.critical(f"Failed to import modules after logging setup: {e}.", exc_info=True)
    # Specifically check if automator_main failed
    if 'automator_main' in str(e):
        logger.warning("Could not import 'job_automator.automator_main'. Application phase will be skipped.")
        automator_main = None # Define as None so later checks don't cause NameError
    else:
        sys.exit(f"CRITICAL IMPORT ERROR: {e}.")


def run_scrapers():
    """Runs all configured job scrapers."""
    logger.info("----- Starting Scraper Run -----")
    # LinkedIn Scraper
    try:
        if config.LINKEDIN_SESSION_COOKIE:
            logger.info("Starting LinkedIn scraper...")
            # Assuming run_linkedin_scraper handles internal errors and logging
            linkedin_scraper.run_linkedin_scraper(limit=config.SCRAPER_JOB_LIMIT)
            logger.info("LinkedIn scraper finished.")
        else:
            logger.warning("LinkedIn scraper skipped: LINKEDIN_SESSION_COOKIE not configured.")
    except Exception as e:
        # Catch errors during the *call* to the scraper function if needed
        # Specific errors like InvalidCookie are handled inside based on previous logs
        if "InvalidCookieException" in str(e): logger.error(f"LinkedIn scraping failed: Invalid Cookie.")
        elif "InvalidArgumentException" in str(e): logger.error(f"LinkedIn scraping failed: Browser/Driver incompatibility.")
        else: logger.error(f"Error running LinkedIn scraper: {e}", exc_info=True)

    # JobRight Scraper
    try:
        if config.JOBRIGHT_COOKIE_STRING:
            logger.info("Starting JobRight scraper...")
            # Assuming run_jobright_scraper handles internal errors and logging
            jobright_scraper.run_jobright_scraper(max_position=config.JOBRIGHT_MAX_POSITION)
            logger.info("JobRight scraper finished.")
        else:
            logger.warning("JobRight scraper skipped: JOBRIGHT_COOKIE_STRING not configured.")
    except Exception as e:
        logger.error(f"Error running JobRight scraper: {e}", exc_info=True)

    logger.info("----- Scraper Run Finished -----")


def process_single_job(job_data):
    """
    Processes a single job: Determines output dir, tailors docs, generates PDFs via generator.
    Updates DB status. Returns True on success, False on failure.
    """
    primary_id = job_data.get('primary_identifier')
    job_db_id = job_data.get('_id') # MongoDB's internal ID
    job_title = job_data.get('job_title', 'Unknown Job')
    company_name = job_data.get('company_name', 'Unknown Company')

    if not primary_id:
        logger.error(f"Job data (DB ID: {job_db_id}) missing 'primary_identifier'. Cannot process.")
        return False

    log_prefix = f"[{primary_id}] "
    logger.info(f"{log_prefix}Processing job: '{job_title}' at '{company_name}'")

    # --- Determine and Create Job-Specific Output Directory ---
    try:
        base_output_path = PROJECT_ROOT / config.BASE_OUTPUT_DIR_NAME
        create_dir_if_not_exists(base_output_path)
        # Create a unique folder name using sanitized components and DB ID
        id_part_for_name = sanitize_filename_component(str(job_db_id), 24) # Use DB ID for name uniqueness
        job_specific_output_dir_name = f"{sanitize_filename_component(company_name)}_{sanitize_filename_component(job_title)}_{id_part_for_name}"
        job_specific_output_dir = base_output_path / job_specific_output_dir_name
        create_dir_if_not_exists(job_specific_output_dir) # Create the directory HERE
        logger.info(f"{log_prefix}Output directory set: {job_specific_output_dir}")
    except Exception as dir_err:
        logger.error(f"{log_prefix}Failed to create output directory '{job_specific_output_dir}': {dir_err}", exc_info=True)
        database.update_job_status(primary_id, config.JOB_STATUS_ERROR_UNKNOWN, f"Failed create output dir: {dir_err}")
        return False

    # --- Update DB Status and Path ---
    update_fields = {'job_specific_output_dir': str(job_specific_output_dir)}
    if not database.update_job_data(primary_id, update_fields):
        logger.warning(f"{log_prefix}Failed to update DB with output directory path.")
        # Depending on severity, you might want to return False here
    database.update_job_status(primary_id, config.JOB_STATUS_PROCESSING, "Starting tailoring.")

    # --- Step 1: Tailor Resume and Cover Letter ---
    tailored_content = None
    try:
        logger.info(f"{log_prefix}Generating tailored LaTeX documents via tailor module...")
        tailored_content = resume_tailor_module.generate_tailored_latex_docs(job_data)
        if not tailored_content or not tailored_content.get('resume'):
            raise ValueError("Tailor function returned no resume content.") # Raise error to catch below
        logger.info(f"{log_prefix}Tailoring successful. Resume generated. CL {'generated.' if tailored_content.get('cover_letter') else 'not generated.'}")
        update_fields = {
            'tailored_resume_text': tailored_content.get('resume'),
            'tailored_cover_letter_text': tailored_content.get('cover_letter')
        }
        if not database.update_job_data(primary_id, update_fields):
            logger.warning(f"{log_prefix}Failed to update DB with tailored LaTeX text.")
    except Exception as e:
        logger.error(f"{log_prefix}Exception during tailoring: {e}", exc_info=True)
        database.update_job_status(primary_id, config.JOB_STATUS_TAILORING_FAILED, f"Exception in tailor: {str(e)[:200]}")
        return False

    # --- Step 2: Generate PDFs (Passing Path) ---
    try:
        logger.info(f"{log_prefix}Generating PDF documents into: {job_specific_output_dir}...")
        # *** THIS IS THE CORRECTED CALL TO THE MODIFIED GENERATOR ***
        resume_path, cl_path, details_path = document_generator_module.create_documents(
            job_data=job_data,
            tailored_docs_latex=tailored_content,
            target_output_directory=str(job_specific_output_dir) # Pass the string path
        )
        # Check results
        resume_ok = resume_path and Path(resume_path).is_file()
        details_ok = details_path and Path(details_path).is_file()
        if not resume_ok or not details_ok:
            error_msg = f"PDF generation failed: Resume {'missing' if not resume_ok else 'OK'}, Details {'missing' if not details_ok else 'OK'}."
            logger.error(f"{log_prefix}{error_msg}")
            database.update_job_status(primary_id, config.JOB_STATUS_GENERATION_FAILED, error_msg)
            update_fields = {'resume_pdf_path': resume_path, 'cover_letter_pdf_path': cl_path, 'job_details_pdf_path': details_path}
            database.update_job_data(primary_id, update_fields) # Store whatever paths were returned
            return False

        logger.info(f"{log_prefix}PDF generation successful.")
        update_fields = {
            'resume_pdf_path': resume_path, 'cover_letter_pdf_path': cl_path, 'job_details_pdf_path': details_path,
            'job_specific_output_dir': str(job_specific_output_dir), # Ensure path is stored correctly
            'status': config.JOB_STATUS_DOCS_READY, # Ready for application
            'status_reason': f"Docs generated in {job_specific_output_dir.name}",
        }
        database.update_job_data(primary_id, update_fields)
        return True # Success

    except Exception as e:
        logger.error(f"{log_prefix}Exception during PDF generation call: {e}", exc_info=True)
        database.update_job_status(primary_id, config.JOB_STATUS_GENERATION_FAILED, f"Exception calling generator: {str(e)[:200]}")
        return False


def process_retrieved_jobs():
    """Fetches unprocessed jobs from DB and processes them."""
    logger.info("----- Starting Job Processing Run (Tailoring & Docs) -----")
    statuses_to_process = [ config.JOB_STATUS_NEW, config.JOB_STATUS_TAILORING_FAILED, config.JOB_STATUS_GENERATION_FAILED ]
    try: jobs_to_process = database.get_jobs_by_status(statuses_to_process, limit=config.MAX_JOBS_TO_PROCESS_PER_RUN)
    except Exception as db_e: logger.error(f"Failed retrieve jobs from DB: {db_e}", exc_info=True); return
    if not jobs_to_process: logger.info(f"No jobs in states ({', '.join(statuses_to_process)}) to process."); return
    logger.info(f"Found {len(jobs_to_process)} jobs to process.")
    processed_count, success_count = 0, 0
    for job_data in jobs_to_process:
        primary_id = job_data.get('primary_identifier', 'Unknown')
        logger.info(f"--- Starting processing job: {primary_id} ---")
        try:
            if process_single_job(job_data): success_count += 1; logger.info(f"--- Successfully processed job (Docs Ready): {primary_id} ---")
            else: logger.warning(f"--- Failed to process job: {primary_id}. ---")
        except Exception as e:
            logger.critical(f"--- Uncaught exception processing job {primary_id}: {e} ---", exc_info=True)
            if primary_id != 'Unknown':
                 try: database.update_job_status(primary_id, config.JOB_STATUS_ERROR_UNKNOWN, f"Unhandled exception: {str(e)[:200]}")
                 except Exception as db_err: logger.error(f"Failed update error status for {primary_id}: {db_err}")
        finally: processed_count += 1; time.sleep(1.0) # Delay
    logger.info("----- Job Processing Run Finished -----")
    logger.info(f"Attempted: {processed_count} jobs. Docs generated for: {success_count}.")


# --- Application Phase Function ---
def run_application_phase():
    """Fetches jobs ready for application and attempts to apply via job_automator."""
    if not automator_main: logger.error("Job Automator module not loaded. Skipping application phase."); return
    logger.info("----- Starting Job Application Phase -----")
    jobs_to_apply = database.get_jobs_by_status([config.JOB_STATUS_DOCS_READY], limit=config.MAX_JOBS_TO_PROCESS_PER_RUN)
    if not jobs_to_apply: logger.info("No jobs found with status 'docs_ready' to apply."); return
    logger.info(f"Found {len(jobs_to_apply)} jobs ready for application attempt.")
    applied_count, failed_count, easy_apply_count = 0, 0, 0
    # Define and create processed application directories
    processed_base_path = PROJECT_ROOT / config.PROCESSED_APPS_DIR_NAME
    success_path = processed_base_path / config.SUCCESS_DIR_NAME
    failure_path = processed_base_path / config.FAILURE_DIR_NAME
    easy_apply_path = processed_base_path / config.EASY_APPLY_DIR_NAME
    try: [create_dir_if_not_exists(p) for p in [processed_base_path, success_path, failure_path, easy_apply_path]]
    except Exception as e: logger.error(f"Could not create processed app dirs: {e}. Aborting.", exc_info=True); return
    processed_paths_config = { "success": str(success_path), "failure": str(failure_path), "easy_apply": str(easy_apply_path) }

    for job_data in jobs_to_apply:
        primary_id = job_data.get('primary_identifier'); source_dir = job_data.get('job_specific_output_dir')
        if not primary_id: logger.warning(f"Skipping app attempt: missing primary_id (DB ID: {job_data.get('_id')})."); continue
        if not source_dir or not Path(source_dir).is_dir():
            logger.error(f"[{primary_id}] Source doc dir missing/invalid: '{source_dir}'. Cannot apply.");
            database.update_job_status(primary_id, config.JOB_STATUS_ERROR_UNKNOWN, "Source dir missing for app.")
            continue
        logger.info(f"--- Attempting application for job: {primary_id} ---")
        try:
            result_status = automator_main.attempt_application(job_data=job_data, processed_paths=processed_paths_config)
            logger.info(f"--- Application attempt result for {primary_id}: {result_status} ---")
            if result_status == config.JOB_STATUS_APPLIED_SUCCESS: applied_count += 1
            elif result_status == "easy_apply_processed": easy_apply_count += 1
            elif result_status in [config.JOB_STATUS_APP_FAILED_ATS, config.JOB_STATUS_APP_FAILED_MANUAL, config.JOB_STATUS_ERROR_UNKNOWN]: failed_count += 1
            else: logger.warning(f"[{primary_id}] Unexpected result status from automator: {result_status}"); failed_count += 1
        except Exception as e:
            logger.critical(f"--- Uncaught exception during application attempt for {primary_id}: {e} ---", exc_info=True); failed_count += 1
            try: database.update_job_status(primary_id, config.JOB_STATUS_ERROR_UNKNOWN, f"Unhandled exception in app phase: {str(e)[:200]}")
            except Exception as db_err: logger.error(f"Failed update DB status after app error for {primary_id}: {db_err}")
        finally: time.sleep(10) # Delay between applications
    logger.info("----- Job Application Phase Finished -----")
    logger.info(f"Attempted: {len(jobs_to_apply)}, Applied: {applied_count}, Failed/Error: {failed_count}, Easy Apply: {easy_apply_count}")

# --- Main Pipeline ---
def main_pipeline(run_scraping_flag=False):
    start_time = time.time(); logger.info(f"====== Pipeline Start: {datetime.now(timezone.utc).isoformat()} ======")
    db_connected = False
    try:
        logger.info("Connecting to database..."); database.connect_db(); db_connected = True; logger.info("Database connection successful.")
        if run_scraping_flag: logger.info("--- Phase 1: Running Scrapers ---"); run_scrapers()
        else: logger.info("--- Phase 1: Skipping Scrapers (Default) ---")
        logger.info("--- Phase 2: Processing Jobs (Tailoring & PDF Generation) ---"); process_retrieved_jobs()
        logger.info("--- Phase 3: Processing Applications (Applying for Jobs) ---"); run_application_phase()
    except ConnectionError as ce: logger.critical(f"Pipeline aborted: DB connection error: {ce}"); db_connected = False
    except Exception as e: logger.critical(f"Unhandled pipeline exception: {e}", exc_info=True)
    finally:
        if db_connected: logger.info("Closing database connection..."); database.close_db()
        else: logger.info("Skipping DB close (connection likely failed).")
    duration = time.time() - start_time; logger.info(f"====== Pipeline End: {datetime.now(timezone.utc).isoformat()}. Duration: {duration:.2f} sec ======")

# --- Script Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Application Agent Pipeline")
    parser.add_argument("--run-scraping", action="store_true", help="Run scraping phase (default: skip).")
    parser.add_argument("--log-level", default=None, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Override log level.")
    args = parser.parse_args()
    cli_log_level = args.log_level or config.LOG_LEVEL
    try: # Reconfigure logging level if CLI arg is different
         if args.log_level and args.log_level != config.LOG_LEVEL:
             numeric_level = getattr(logging, cli_log_level, None)
             if isinstance(numeric_level, int):
                 logging.getLogger().setLevel(numeric_level);
                 for handler in logging.getLogger().handlers: handler.setLevel(numeric_level)
                 logger.info(f"Logging level overridden by CLI to: {cli_log_level}")
             else: logger.warning(f"Invalid CLI log level: {args.log_level}.")
    except Exception as log_e: logger.error(f"Error reconfiguring logging: {log_e}")
    main_pipeline(run_scraping_flag=args.run_scraping) # Pass the flag value