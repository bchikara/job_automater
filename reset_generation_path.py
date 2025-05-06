import os
import sys
import logging
import traceback

# --- Add Project Root to Path ---
# Ensures modules like 'database' and 'config' can be imported
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Setup Logging ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_LEVEL = logging.INFO
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT, handlers=[logging.StreamHandler()])

# --- Import Database Module ---
try:
    logging.info("Importing config module...")
    import config # Often needed by database module for connection details
    logging.info("Config module imported.")
    logging.info("Importing database module...")
    import database # Assumes database.py is in the same directory
    logging.info("Database module imported.")
except ImportError as e:
    logging.critical(f"Failed to import database or config module: {e}. Make sure this script is in the project root.", exc_info=True)
    sys.exit(1)
except Exception as e:
    logging.critical(f"An unexpected error occurred during imports: {e}", exc_info=True)
    sys.exit(1)


def reset_job_statuses():
    """
    Finds jobs that have attempted document generation (success or fail)
    and resets their status to 'resume_ready', clearing PDF paths.
    """
    logging.info("--- Starting Job Status Reset Script ---")

    # 1. Connect to Database
    logging.info("Attempting to connect to database...")
    try:
        # <<<--- ADDED DEBUGGING PRINT --->>>
        # Print the connection string value *before* it's used by connect_db
        # Use repr() to show hidden characters like quotes or spaces if they exist
        logging.info(f"DEBUG: Value of config.MONGODB_CONNECTION_STRING before connect_db: {repr(config.MONGODB_CONNECTION_STRING)}")

        db_connection_successful = database.connect_db()
        logging.info(f"Database connection attempt finished. Reported success: {db_connection_successful}")
    except Exception as db_conn_err:
        logging.critical(f"CRITICAL ERROR during database.connect_db() call: {db_conn_err}", exc_info=True)
        # Print the connection string again in case of error
        logging.error(f"DEBUG: Value of config.MONGODB_CONNECTION_STRING during connect_db error: {repr(config.MONGODB_CONNECTION_STRING)}")
        return # Cannot proceed

    jobs_collection = database.jobs_collection
    if jobs_collection is None:
        logging.critical("MongoDB collection object (database.jobs_collection) is None. Cannot proceed.")
        return

    logging.info(f"Connected to DB: {config.DB_NAME}, Collection: {jobs_collection.name}")

    # 2. Define Query and Update Operations
    # Find jobs that have reached a document generation stage (success or failure)
    # Add any other statuses you want to reset to this list
    statuses_to_reset = [
        'documents_generated',
        'generation_failed',
        'resume_generated_cl_failed', # Example if you added this status
        'generation_skipped_no_text'
    ]
    query = {
        'status': {'$in': statuses_to_reset}
    }

    # Set status back and clear paths
    update_operation = {
        '$set': {
            'status': 'resume_ready',
            'resume_pdf_path': None,
            'cover_letter_pdf_path': None,
            'documents_generated_at': None, # Clear timestamps too if desired
            'generation_error_at': None
        }
        # Use '$unset' if you prefer to completely remove the fields:
        # '$unset': {
        #     'resume_pdf_path': "",
        #     'cover_letter_pdf_path': "",
        #     'documents_generated_at': "",
        #     'generation_error_at': ""
        # }
    }

    # 3. Execute Update
    logging.info(f"Attempting to reset jobs with status in {statuses_to_reset}...")
    try:
        update_result = jobs_collection.update_many(query, update_operation)

        logging.info("--- Reset Operation Summary ---")
        logging.info(f"Documents matched for reset: {update_result.matched_count}")
        logging.info(f"Documents modified: {update_result.modified_count}")

        if update_result.matched_count > 0 and update_result.modified_count == 0:
             logging.warning("Matched documents but modified count is 0. They might have already been reset.")
        elif update_result.matched_count == 0:
             logging.info("No documents found matching the criteria to reset.")

    except Exception as e:
        logging.error(f"An error occurred during the MongoDB update operation: {e}", exc_info=True)

    # 4. Close Connection
    finally:
        logging.info("Attempting to close database connection...")
        try:
            database.close_db()
            logging.info("Database connection closed.")
        except Exception as db_close_err:
            logging.error(f"Error during database.close_db(): {db_close_err}", exc_info=True)

    logging.info("--- Job Status Reset Script Finished ---")


if __name__ == "__main__":
    reset_job_statuses()
