# database.py
import pymongo
import datetime
import logging
import re
from urllib.parse import urlparse, parse_qs, urlunparse, quote_plus

# Import configuration variables including status constants
import config

# Setup logger for this module
logger = logging.getLogger(__name__)

# Global MongoDB variables
mongo_client = None
db = None
jobs_collection = None

def connect_db():
    """Establishes connection to MongoDB and gets the jobs collection."""
    global mongo_client, db, jobs_collection
    if mongo_client is not None and jobs_collection is not None: # Correct check
        return jobs_collection

    logger.info("Attempting to establish MongoDB connection...")
    try:
        conn_str = config.MONGODB_CONNECTION_STRING
        db_name = config.DB_NAME
        logger.debug(f"Raw MONGODB_CONNECTION_STRING from config: {repr(conn_str)}")
        if not conn_str or not isinstance(conn_str, str): raise ValueError(f"MONGODB_CONNECTION_STRING invalid: {repr(conn_str)}")
        if not db_name or not isinstance(db_name, str): raise ValueError(f"DB_NAME invalid: {repr(db_name)}")
        conn_str = conn_str.strip()
        if not conn_str.startswith(('mongodb://', 'mongodb+srv://')):
            raise pymongo.errors.InvalidURI(f"Invalid URI scheme. Received: {repr(conn_str)}")

        logger.info(f"Connecting to MongoDB using URI: {conn_str[:30]}... Database: {db_name}")
        mongo_client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=10000)
        mongo_client.admin.command('ismaster') # Verify connection
        logger.info("MongoDB server ping successful.")
        db = mongo_client[db_name]
        jobs_collection = db["jobs"]
        logger.info(f"MongoDB connection successful. Using DB: '{db_name}', Collection: 'jobs'")
        ensure_indexes()
    except ValueError as ve:
        logger.critical(f"MongoDB configuration error: {ve}"); mongo_client = db = jobs_collection = None; raise ConnectionError(f"Config error: {ve}")
    except pymongo.errors.InvalidURI as uri_err:
        logger.critical(f"MongoDB Invalid URI Error: {uri_err}. Check .env."); mongo_client = db = jobs_collection = None; raise ConnectionError(f"Invalid URI: {uri_err}")
    except (pymongo.errors.ConnectionFailure, pymongo.errors.ServerSelectionTimeoutError) as conn_err:
        logger.critical(f"MongoDB connection failed: {conn_err}"); mongo_client = db = jobs_collection = None; raise ConnectionError(f"Connection failed: {conn_err}")
    except Exception as e:
        logger.critical(f"Unexpected MongoDB connection error: {e}", exc_info=True); mongo_client = db = jobs_collection = None; raise ConnectionError(f"Unexpected connection error: {e}")
    return jobs_collection

def close_db():
    """Closes the MongoDB connection."""
    global mongo_client, db, jobs_collection
    if mongo_client:
        try: mongo_client.close(); logger.info("MongoDB connection closed.")
        except Exception as e: logger.error(f"Error closing MongoDB connection: {e}", exc_info=True)
        finally: mongo_client = db = jobs_collection = None; logger.debug("Global DB variables reset.")
    else: logger.debug("No active MongoDB connection to close.")

def ensure_indexes():
    """Ensures necessary indexes exist on the jobs collection."""
    if jobs_collection is None: logger.warning("Cannot ensure indexes: jobs_collection is None."); return
    try:
        jobs_collection.create_indexes([
            pymongo.IndexModel([("primary_identifier", pymongo.ASCENDING)], name="primary_id_unique_idx", unique=True),
            pymongo.IndexModel([("status", pymongo.ASCENDING)], name="status_idx"),
            pymongo.IndexModel([("source_platform", pymongo.ASCENDING)], name="source_platform_idx"),
            pymongo.IndexModel([("date_scraped", pymongo.DESCENDING)], name="date_scraped_idx"),
            pymongo.IndexModel([("source_job_id", pymongo.ASCENDING)], name="job_id_idx", sparse=True),
            pymongo.IndexModel([("last_updated", pymongo.DESCENDING)], name="last_updated_idx")
        ])
        logger.info("Database indexes ensured.")
    except pymongo.errors.OperationFailure as e:
        if "already exists" in str(e): logger.info(f"Index operation notice: {e}")
        else: logger.error(f"Error creating/ensuring indexes: {e}", exc_info=True)
    except Exception as e: logger.error(f"Unexpected error during index creation/check: {e}", exc_info=True)

def normalize_url(url_string):
    """ Normalizes a URL for consistent primary_identifier generation. """
    if not url_string or not isinstance(url_string, str): return None
    try:
        url_string = url_string.strip()
        if "linkedin.com/jobs/view/" in url_string:
            match = re.search(r"(linkedin\.com/jobs/view/\d+)", url_string);
            if match: return "https://" + match.group(1)
        parsed = urlparse(url_string); scheme = parsed.scheme or 'https'; netloc = parsed.netloc.lower().replace('www.','')
        if "indeed.com" in netloc:
             query_params = parse_qs(parsed.query); job_key = query_params.get('jk', [None])[0]
             if job_key: return urlunparse((scheme, netloc, parsed.path, '', f"jk={job_key}", ''))
        clean_path = parsed.path;
        if len(clean_path) > 1 and clean_path.endswith('/'): clean_path = clean_path[:-1]
        return urlunparse((scheme, netloc, clean_path, '', '', ''))
    except Exception as e: logger.warning(f"Could not normalize URL '{url_string}': {e}"); return url_string

def store_job_data(job_data):
    """ Stores job data using 'source_url' for primary_id. Sets status to NEW. Returns DB _id or None. """
    collection = connect_db()
    if collection is None: # Corrected check
         logger.error("DB: Cannot store job data - no connection."); return None
    source_url = job_data.get("source_url")
    if not source_url: logger.warning(f"DB: Job data missing 'source_url' for '{job_data.get('job_title')}'. Skipping."); return None
    primary_id = normalize_url(source_url)
    if not primary_id: logger.warning(f"DB: Could not normalize source_url '{source_url}'. Skipping."); return None
    doc_to_store = job_data.copy(); now = datetime.datetime.now(datetime.timezone.utc)
    doc_to_store['primary_identifier'] = primary_id; doc_to_store['last_updated'] = now
    if not doc_to_store.get('job_title') or not doc_to_store.get('company_name'): logger.warning(f"DB: Skipping '{primary_id}', missing title/company."); return None
    update_op = {'$set': doc_to_store, '$addToSet': {'sources_list': doc_to_store.get('source_platform')},
                 '$setOnInsert': {'date_scraped': now, 'status': config.JOB_STATUS_NEW, 'status_reason': "Newly scraped",
                                 'application_attempts': 0, 'tailored_resume_text': None, 'tailored_cover_letter_text': None,
                                 'resume_pdf_path': None, 'cover_letter_pdf_path': None, 'job_details_pdf_path': None,
                                 'job_specific_output_dir': None, 'application_summary': None, 'error_log': None,}}
    try:
        result = collection.update_one({'primary_identifier': primary_id}, update_op, upsert=True)
        if result.upserted_id: logger.info(f"DB: NEW job stored: '{doc_to_store.get('job_title')}' ID: {result.upserted_id}"); return result.upserted_id
        elif result.matched_count > 0: doc = collection.find_one({'primary_identifier': primary_id}, {'_id': 1}); return doc['_id'] if doc else None
        else: logger.warning(f"DB: Upsert reported no match/upsert for {primary_id}."); return None
    except pymongo.errors.DuplicateKeyError: logger.warning(f"DB: DuplicateKeyError (race?) for {primary_id}. Re-fetching ID."); doc = collection.find_one({'primary_identifier': primary_id}, {'_id': 1}); return doc['_id'] if doc else None
    except Exception as e: logger.error(f"DB: Failed store/update for {primary_id}: {e}", exc_info=True); return None

def update_job_data(primary_id, update_dict):
    """ Updates specific fields for a job by primary_identifier. """
    collection = connect_db();
    if collection is None: logger.error(f"DB: Cannot update job {primary_id}, no connection."); return False # Corrected check
    if not primary_id or not update_dict: logger.error("DB: Cannot update job data, missing primary_id or update_dict."); return False
    update_dict['last_updated'] = datetime.datetime.now(datetime.timezone.utc)
    try:
        result = collection.update_one({'primary_identifier': primary_id}, {'$set': update_dict})
        if result.matched_count == 0: logger.warning(f"DB: Job {primary_id} not found for data update."); return False
        return True
    except Exception as e: logger.error(f"DB: Error updating job {primary_id}: {e}", exc_info=True); return False

def update_job_status(primary_id, status, status_reason=""):
    """ Updates the status and status_reason of a job. """
    logger.info(f"DB: Updating status for {primary_id} to '{status}'. Reason: '{status_reason[:100]}'")
    return update_job_data(primary_id, {'status': status, 'status_reason': status_reason})

def get_jobs_by_status(status_list, limit=5):
    """ Fetches jobs by status, oldest first ('date_scraped'). """
    collection = connect_db()
    # --- THIS IS THE CORRECTED LINE ---
    if collection is None:
    # --- ---
        logger.error("DB: Cannot fetch jobs by status - no connection.")
        return [] # Return empty list if no connection

    if isinstance(status_list, str): status_list = [status_list]
    try:
        cursor = collection.find({'status': {'$in': status_list}}).sort('date_scraped', pymongo.ASCENDING).limit(limit)
        return list(cursor)
    except Exception as e: logger.error(f"DB: Error fetching jobs status {status_list}: {e}", exc_info=True); return []

def get_job_by_primary_id(primary_id):
    """ Fetches a single job by its primary_identifier. """
    collection = connect_db();
    if collection is None: logger.error(f"DB: Cannot fetch job {primary_id}, no connection."); return None # Corrected check
    if not primary_id: logger.warning("DB: Cannot fetch job, primary_id is missing."); return None
    try: return collection.find_one({'primary_identifier': primary_id})
    except Exception as e: logger.error(f"DB: Error fetching job {primary_id}: {e}", exc_info=True); return None