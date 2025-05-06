import os
import sys
import logging
import time
import traceback
# Import specific components from datetime needed
from datetime import datetime, timezone, timedelta

# --- Import Custom Modules ---
# Add the project root to the Python path to allow imports from sibling directories
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Configuration ---
# Setup basic logging first to catch import issues
LOG_FORMAT = '%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S' # Match the user's log format
LOG_LEVEL = logging.INFO
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, handlers=[logging.StreamHandler()])
logging.info("--- main.py execution started: Basic logging configured ---") # Log start immediately

try:
    # Import project modules after basic logging is set up
    logging.info("Importing config module...")
    import config # Ensure config is loaded first
    logging.info("Config module imported.")

    logging.info("Importing database module...")
    import database # Assumes database.py is in the same directory or accessible via PYTHONPATH
    logging.info("Database module imported.")

    logging.info("Importing scrapers module...")
    from scrapers import linkedin_scraper, jobright_scraper
    logging.info("Scrapers module imported.")

    logging.info("Importing resume_tailor module...")
    from resume_tailor import tailor
    logging.info("resume_tailor module imported successfully.")

    import document_generator.generator as generator # Assumes generator.py is inside document_generator/
    logging.info("document_generator module imported successfully.")

except ImportError as e:
    print(f"FATAL ERROR: Could not import necessary modules. Check structure and PYTHONPATH. Error: {e}")
    logging.critical(f"Failed to import core modules: {e}", exc_info=True) # Also log it
    sys.exit(1) # Use sys.exit for clearer exit status
except Exception as e:
     print(f"FATAL ERROR: An unexpected error occurred during initial imports: {e}")
     logging.critical(f"An unexpected error occurred during initial imports: {e}", exc_info=True) # Also log it
     sys.exit(1) # Use sys.exit

# --- Helper Functions ---

def setup_additional_logging():
    """Configures logging levels for libraries after initial setup."""
    logging.info("Setting logging levels for libraries...")
    # Silence verbose logs from libraries if desired
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('dotenv').setLevel(logging.INFO)
    logging.getLogger('li').setLevel(logging.INFO)
    logging.getLogger('PyPDF2').setLevel(logging.ERROR)
    logging.getLogger('google.generativeai').setLevel(logging.INFO) # Log Gemini info
    logging.getLogger('reportlab').setLevel(logging.WARNING) # Silence reportlab info logs
    logging.info("Library logging levels set.") # Confirm completion


def run_scraping_process():
    """Runs all configured scrapers."""
    logging.info("--- Starting Scraping Phase ---")
    try:
        # Run LinkedIn Scraper (Optional - uncomment if needed)
        # linkedin_scraper.run_linkedin_scraper(limit=config.LINKEDIN_JOB_LIMIT_PER_QUERY)

        # Run JobRight API Scraper
        jobright_scraper.run_jobright_scraper(max_position=config.JOBRIGHT_MAX_POSITION)

        # Add calls to other scrapers here in the future
        # e.g., indeed_scraper.run_indeed_scraper(...)

    except Exception as e:
        logging.error(f"An error occurred during the scraping phase: {e}", exc_info=True)
    logging.info("--- Scraping Phase Finished ---")


def run_tailoring_process():
    """Queries DB for scraped jobs and attempts to tailor resumes."""
    logging.info("--- Starting Resume Tailoring Phase ---")
    jobs_collection = database.jobs_collection # Use established connection
    if jobs_collection is None:
        logging.error("MongoDB collection not available. Skipping tailoring phase.")
        return

    logging.info("Querying database for jobs with status 'scraped'...")
    try:
        # Find jobs that have been scraped but not yet tailored
        jobs_to_tailor = list(jobs_collection.find({'status': 'scraped'})) # Limit? .limit(5)
        logging.info(f"Found {len(jobs_to_tailor)} jobs with status 'scraped' to tailor.")
    except Exception as e:
        logging.error(f"Failed to query MongoDB for jobs to tailor: {e}", exc_info=True)
        return # Cannot proceed without jobs

    if not jobs_to_tailor:
        logging.info("No jobs found needing resume tailoring.")
        return

    processed_count = 0
    success_count = 0
    fail_count = 0

    logging.info(f"Starting loop to process {len(jobs_to_tailor)} jobs for resume tailoring...")
    for job in jobs_to_tailor:
        processed_count += 1
        job_id = job.get('_id')
        job_title = job.get('job_title', 'N/A') # Use job_title consistently
        company = job.get('company_name', 'N/A')
        logging.info(f"({processed_count}/{len(jobs_to_tailor)}) Attempting to tailor resume for job: '{job_title}' at '{company}' (ID: {job_id})")

        # Call the tailoring function from resume_tailor/tailor.py
        # This function should handle loading the base resume AND escaping content
        tailored_resume_content = tailor.generate_tailored_resume_text(job) # Pass the job dict

        # Update the database based on the result
        update_fields = {}
        if tailored_resume_content:
            update_fields['status'] = 'resume_ready' # Ready for PDF generation
            update_fields['tailored_resume_text'] = tailored_resume_content # Store the escaped LaTeX
            update_fields['tailored_at'] = datetime.now(timezone.utc) # Use timezone aware
            success_count += 1
            logging.info(f"  Successfully generated tailored resume text for job: '{job_title}'")
        else:
            update_fields['status'] = 'tailoring_failed'
            update_fields['tailoring_error_at'] = datetime.now(timezone.utc) # Use timezone aware
            update_fields['tailored_resume_text'] = None # Ensure it's cleared on failure
            fail_count += 1
            logging.error(f"  Failed to generate tailored resume text for job: '{job_title}'")

        try:
            # Update the specific job document in MongoDB
            logging.debug(f"  Updating job {job_id} status to '{update_fields['status']}'...")
            update_result = jobs_collection.update_one(
                {'_id': job_id},
                {'$set': update_fields}
            )
            if update_result.matched_count == 0:
                 logging.warning(f"  Job ID {job_id} not found for status update.")
            elif update_result.modified_count == 0:
                 logging.warning(f"  Job ID {job_id} found but status was not modified (likely already set).")
            else:
                 logging.debug(f"  MongoDB update result for {job_id}: Matched={update_result.matched_count}, Modified={update_result.modified_count}")

        except Exception as e:
            logging.error(f"  Failed to update MongoDB status for job {job_id} after tailoring attempt: {e}", exc_info=True)
            if tailored_resume_content: success_count -= 1
            fail_count = fail_count + 1 if not tailored_resume_content else fail_count

        logging.debug("Waiting 1 second before next tailoring request...")
        time.sleep(1)

    logging.info(f"--- Resume Tailoring Phase Finished ---")
    logging.info(f"--- Processed: {processed_count}, Succeeded: {success_count}, Failed: {fail_count} ---")


def run_document_generation_process():
    """Queries DB for jobs with tailored resumes and generates PDF documents."""
    logging.info("--- Starting Document Generation Phase ---")
    jobs_collection = database.jobs_collection # Use established connection
    if jobs_collection is None:
        logging.error("MongoDB collection not available. Skipping document generation phase.")
        return

    logging.info("Querying database for jobs with status 'resume_ready'...")
    try:
        jobs_to_process = list(jobs_collection.find({'status': 'resume_ready'}))
        logging.info(f"Found {len(jobs_to_process)} jobs with status 'resume_ready' for document generation.")
    except Exception as e:
        logging.error(f"Failed to query MongoDB for jobs to generate documents: {e}", exc_info=True)
        return

    if not jobs_to_process:
        logging.info("No jobs found needing document generation.")
        return

    processed_count = 0
    success_count = 0
    fail_count = 0

    logging.info(f"Starting loop to process {len(jobs_to_process)} jobs for document generation...")
    for job in jobs_to_process:
        processed_count += 1
        job_id = job.get('_id')
        job_title = job.get('job_title', 'N/A')
        company = job.get('company_name', 'N/A')
        # Get the pre-escaped LaTeX text from the database
        tailored_resume_text = job.get('tailored_resume_text')

        logging.info(f"({processed_count}/{len(jobs_to_process)}) Attempting document generation for job: '{job_title}' at '{company}' (ID: {job_id})")

        if not tailored_resume_text:
            logging.error(f"  Skipping document generation for job {job_id}: Missing tailored_resume_text in database record.")
            fail_count += 1
            try:
                jobs_collection.update_one(
                    {'_id': job_id},
                    {'$set': {'status': 'generation_skipped_no_text', 'generation_error_at': datetime.now(timezone.utc)}}
                )
            except Exception as db_upd_err:
                 logging.error(f"  Failed to update status for skipped job {job_id}: {db_upd_err}")
            continue

        # Call the document generation function - it expects pre-escaped resume text
        resume_pdf_path, cover_letter_pdf_path = generator.create_documents(job, tailored_resume_text)

        # Update the database based on the result
        update_fields = {}
        if resume_pdf_path: # Success primarily depends on resume generation
            update_fields['status'] = 'documents_generated'
            update_fields['resume_pdf_path'] = resume_pdf_path
            if cover_letter_pdf_path:
                update_fields['cover_letter_pdf_path'] = cover_letter_pdf_path
            else:
                update_fields['cover_letter_pdf_path'] = None
                logging.warning(f"  Cover letter generation failed for job {job_id}, but resume was generated.")

            update_fields['documents_generated_at'] = datetime.now(timezone.utc)
            success_count += 1
            logging.info(f"  Successfully generated documents for job: '{job_title}' (Resume: {resume_pdf_path}, CL: {cover_letter_pdf_path})")
        else:
            update_fields['status'] = 'generation_failed'
            update_fields['generation_error_at'] = datetime.now(timezone.utc)
            update_fields['resume_pdf_path'] = None
            update_fields['cover_letter_pdf_path'] = None
            fail_count += 1
            logging.error(f"  Failed to generate documents (specifically resume) for job: '{job_title}'")

        try:
            logging.debug(f"  Updating job {job_id} status to '{update_fields['status']}'...")
            update_result = jobs_collection.update_one(
                {'_id': job_id},
                {'$set': update_fields}
            )
            if update_result.matched_count == 0:
                 logging.warning(f"  Job ID {job_id} not found for status update after document generation.")
            elif update_result.modified_count == 0:
                 logging.warning(f"  Job ID {job_id} found but status was not modified after document generation (likely already set).")
            else:
                 logging.debug(f"  MongoDB update result for {job_id}: Matched={update_result.matched_count}, Modified={update_result.modified_count}")

        except Exception as e:
            logging.error(f"  Failed to update MongoDB status for job {job_id} after document generation attempt: {e}", exc_info=True)
            if resume_pdf_path: success_count -= 1
            fail_count = fail_count + 1 if not resume_pdf_path else fail_count

        # time.sleep(0.5) # Optional delay

    logging.info(f"--- Document Generation Phase Finished ---")
    logging.info(f"--- Processed: {processed_count}, Succeeded: {success_count}, Failed: {fail_count} ---")


# --- Script Entry Point ---
if __name__ == "__main__":
    logging.info("Entered main execution block (if __name__ == '__main__').")
    start_time = time.time()
    setup_additional_logging()
    logging.info("Starting job processing pipeline...")

    logging.info("Attempting to connect to database via database.connect_db()...")
    db_connection_successful = None
    try:
        db_connection_successful = database.connect_db()
        logging.info(f"Database connection attempt finished. Reported success: {db_connection_successful}")
    except Exception as db_conn_err:
        logging.critical(f"CRITICAL ERROR during database.connect_db() call: {db_conn_err}", exc_info=True)
        db_connection_successful = False

    if database.jobs_collection is None:
         logging.critical("CRITICAL ERROR: MongoDB collection object (database.jobs_collection) is None. Connection likely failed or collection not set in database module. Cannot proceed.")
         logging.info(f"(Debug info: connect_db function returned: {db_connection_successful})")
    else:
        logging.info(f"Successfully connected/verified MongoDB database: {config.DB_NAME}, collection: {database.jobs_collection.name}")
        logging.info("Proceeding to pipeline steps...")
        try:
            # Step 1: Scrape Jobs (Optional)
            # logging.info("Skipping scraping phase as configured.")
            # run_scraping_process()

            # Step 2: Tailor Resumes
            # logging.info("Attempting to run tailoring process...")
            # run_tailoring_process()
            # logging.info("Tailoring process finished.")

            # Step 3: Generate Documents
            logging.info("Attempting to run document generation process...")
            run_document_generation_process()
            logging.info("Document generation process finished.")

            # Step 4: Apply for Jobs (Future)
            # logging.info("Skipping application process (Future Implementation).")

        except Exception as e:
            logging.critical(f"An uncaught exception occurred during the pipeline execution steps: {e}", exc_info=True)
        finally:
            logging.info("Attempting to close database connection via database.close_db()...")
            try:
                database.close_db()
                logging.info("Database close function call completed.")
            except Exception as db_close_err:
                 logging.error(f"Error during database.close_db(): {db_close_err}", exc_info=True)

    end_time = time.time()
    duration = end_time - start_time
    logging.info(f"Job processing pipeline finished in {duration:.2f} seconds.")
    logging.info("--- main.py execution finished ---")

