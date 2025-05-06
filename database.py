# database.py
import pymongo
import datetime
import logging
from urllib.parse import urlparse, parse_qs, urlunparse

# Import configuration variables
import config

mongo_client = None
db = None
jobs_collection = None

def connect_db():
    """Establishes connection to MongoDB and gets the collection."""
    global mongo_client, db, jobs_collection
    logging.info("Entering connect_db function...") # Log entry
    if mongo_client is None: # Connect only if not already connected
        try:
            logging.info(f"Attempting MongoDB connection to {config.MONGODB_CONNECTION_STRING[:20]}... with timeout 10s")
            mongo_client = pymongo.MongoClient(config.MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=10000)

            logging.info("Pinging MongoDB server (ismaster command)...")
            mongo_client.admin.command('ismaster') # Verify connection
            logging.info("MongoDB server ping successful.")

            db = mongo_client[config.DB_NAME]
            jobs_collection = db["jobs"]
            logging.info(f"MongoDB connection successful. DB: '{config.DB_NAME}', Collection: 'jobs'")

            # Ensure indexes exist after successful connection
            ensure_indexes()

        except pymongo.errors.ServerSelectionTimeoutError as err:
             logging.error(f"MongoDB connection failed: Timeout - {err}")
             mongo_client = None
             db = None
             jobs_collection = None
        except pymongo.errors.ConnectionFailure as e:
            logging.error(f"ERROR: Could not connect to MongoDB: {e}")
            mongo_client = None
            db = None
            jobs_collection = None
        except Exception as e:
            # Capture the specific error during index creation here as well
            logging.error(f"ERROR: An unexpected error occurred during MongoDB setup or index creation: {e}", exc_info=True)
            mongo_client = None
            db = None
            jobs_collection = None
    else:
        logging.info("MongoDB connection already established.")

    logging.info("Exiting connect_db function.") # Log exit
    return jobs_collection # Return the collection object or None

def ensure_indexes():
    """Creates necessary indexes if they don't exist."""
    logging.info("Entering ensure_indexes function...") # Log entry
    # Check if the global variable is set and is a Collection instance
    if not isinstance(jobs_collection, pymongo.collection.Collection):
        logging.error("Cannot ensure indexes, MongoDB collection object is invalid or None.")
        # Raising an error might be better here as indexes are important.
        raise ConnectionError("MongoDB collection is invalid or None, cannot ensure indexes.")

    logging.info("Ensuring database indexes...")
    try:
        index_info = jobs_collection.index_information()
        logging.debug(f"Existing indexes: {index_info}") # Log existing indexes

        # Ensure primary_identifier index exists and is unique
        if "primary_identifier_1" not in index_info:
            logging.info("Creating unique index on 'primary_identifier'...")
            jobs_collection.create_index("primary_identifier", unique=True, name="primary_identifier_1")
            logging.info("Created unique index on 'primary_identifier'.")
        elif not index_info["primary_identifier_1"].get("unique"):
             logging.warning("Index 'primary_identifier_1' exists but is not unique. Attempting to recreate.")
             # Dropping and recreating indexes should be done with caution on production data
             jobs_collection.drop_index("primary_identifier_1")
             jobs_collection.create_index("primary_identifier", unique=True, name="primary_identifier_1")
             logging.info("Recreated unique index on 'primary_identifier'.")
        else:
            logging.info("Unique index on 'primary_identifier' already exists.")

        # Ensure status index exists (doesn't need to be unique)
        if "status_1" not in index_info:
             logging.info("Creating index on 'status'...")
             jobs_collection.create_index("status", name="status_1")
             logging.info("Created index on 'status'.")
        else:
            logging.info("Index on 'status' already exists.")

        logging.info("Database indexes are ensured.")

    except Exception as e:
        # Catch errors during index creation specifically
        logging.error(f"Error ensuring MongoDB indexes: {e}", exc_info=True)
        # Optionally re-raise the exception if index creation failure is critical
        raise e # Re-raise to indicate a critical setup failure
    logging.info("Exiting ensure_indexes function.") # Log exit


def close_db():
    """Closes the MongoDB connection."""
    global mongo_client, db, jobs_collection
    logging.info("Entering close_db function...") # Log entry
    if mongo_client:
        try:
            mongo_client.close()
            logging.info("MongoDB connection closed.")
        except Exception as e:
            logging.error(f"Error closing MongoDB connection: {e}", exc_info=True)
        finally:
            # Reset global variables regardless of close success/failure
            mongo_client = None
            db = None
            jobs_collection = None
            logging.info("Global DB variables reset.")
    else:
        logging.info("No active MongoDB connection to close.")
    logging.info("Exiting close_db function.") # Log exit

def normalize_url(url):
    """Removes common tracking parameters and normalizes a URL."""
    if not url or not isinstance(url, str):
        return None
    try:
        # Pre-processing: remove potential extra whitespace
        url = url.strip()
        parsed = urlparse(url)

        # Ensure scheme is present, default to https
        scheme = parsed.scheme if parsed.scheme else 'https'

        # Normalize netloc: lowercase, remove www.
        netloc = parsed.netloc.lower().replace('www.', '')

        # Normalize path: remove trailing slash unless it's the root path
        path = parsed.path
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]

        # Filter query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        params_to_remove = {'utm_', 'ref', 'trk', 'source', 'hmb_', 'hsa_', 'gclid', 'fbclid', 'position', 'pagenum', 'srcid', 'trkparam', 'refid', 'trackingid', 'mcid', 'mktid'}
        filtered_params = {}
        for k, v in query_params.items():
            if not k: continue # Skip keys that are None or empty
            k_lower = k.lower()
            should_remove = False
            for prefix in params_to_remove:
                if k_lower.startswith(prefix):
                    should_remove = True
                    break
            if not should_remove:
                # Take only the first value if multiple exist for the same key
                filtered_params[k] = v[0] if v else ''

        # Rebuild the query string consistently: sort keys, encode values if needed
        # Use urlencode for proper encoding
        from urllib.parse import urlencode
        new_query = urlencode(sorted(filtered_params.items()))

        # Reconstruct the URL
        # Fragment is usually not relevant for identification, often removed
        fragment = '' # parsed.fragment
        url = urlunparse((scheme, netloc, path, parsed.params, new_query, fragment))
        return url
    except Exception as e:
        logging.warning(f"Could not normalize URL '{url}': {e}")
        return url # Return original URL if parsing fails

def generate_primary_identifier(job_data):
    """Generates the primary identifier for deduplication based on available data."""
    app_type = job_data.get("application_type")
    app_url = job_data.get("application_url")
    source_platform = job_data.get("source_platform")
    source_job_id = job_data.get("source_job_id")
    source_url = job_data.get("source_url") # URL of the job listing on the source platform

    # Priority 1: Normalized External Application URL
    if app_type == "external" and app_url:
        normalized = normalize_url(app_url)
        if normalized:
            # Further check: ensure it's not just a link back to the source platform listing
            if source_platform == "linkedin" and "linkedin.com/jobs/view" in normalized:
                 logging.debug(f"External link {normalized} appears to be a LinkedIn view link, treating as Easy Apply for ID generation.")
                 # Fall through to Easy Apply logic below
                 pass
            else:
                logging.debug(f"Generated identifier from normalized external URL: {normalized}")
                return normalized
        else:
             logging.warning(f"Using non-normalized external URL for identifier: {app_url}")
             return app_url # Fallback to non-normalized URL

    # Priority 2: Easy Apply Identifier (or external link that resolved back to source listing)
    if (app_type == "easy_apply" or (app_type == "external" and normalize_url(app_url) == normalize_url(source_url))) \
       and source_platform and source_job_id:
        identifier = f"{source_platform}_easyapply:{source_job_id}"
        logging.debug(f"Generated identifier for Easy Apply / Source Link: {identifier}")
        return identifier

    # Fallback 3: Use Normalized Source URL if no other identifier worked
    if source_platform and source_url:
        normalized_source = normalize_url(source_url)
        if normalized_source:
             logging.warning(f"Generating fallback identifier from normalized source URL: {normalized_source}")
             return normalized_source

    # Fallback 4: Use Source ID if available (less ideal than source URL)
    if source_platform and source_job_id:
         identifier = f"{source_platform}_sourceid:{source_job_id}"
         logging.warning(f"Generating fallback identifier from source platform and ID: {identifier}")
         return identifier

    # Fallback 5: Generate from key fields (least reliable)
    company = job_data.get("company_name", "unknown").lower().replace(" ", "")
    title = job_data.get("job_title", "unknown").lower().replace(" ", "")
    location = job_data.get("location", "unknown").lower().replace(" ", "")
    fallback_id = f"fallback:{company[:20]}_{title[:30]}_{location[:20]}"
    logging.error(f"Cannot generate reliable primary identifier for job: {title} at {company}. Using least reliable fallback: {fallback_id}")
    return fallback_id


def store_job_data(job_data):
    """Stores formatted job data into MongoDB using upsert for deduplication."""
    collection = connect_db() # Ensure DB connection and get collection
    if collection is None: # Check if connection failed
        logging.error("MongoDB collection not available (connection failed). Skipping storage.")
        return False # Indicate failure or skip

    primary_id = generate_primary_identifier(job_data)
    if not primary_id:
        logging.error(f"Skipping job due to missing primary identifier: {job_data.get('job_title')}")
        return False # Indicate failure or skip

    # Ensure essential fields are present before storing
    if not job_data.get('job_title') or not job_data.get('company_name'):
         logging.warning(f"Skipping job '{primary_id}' due to missing title or company.")
         return False

    # Prepare the document for storage
    doc_to_store = job_data.copy() # Avoid modifying original dict
    doc_to_store['primary_identifier'] = primary_id
    doc_to_store['scraped_at'] = datetime.datetime.now(datetime.timezone.utc)

    # Fields to set only on insert
    insert_data = {
        **doc_to_store, # Include all fields from job_data dict
        'status': 'scraped', # Initial status
        'created_at': datetime.datetime.now(datetime.timezone.utc)
    }
    # Fields to update on match or insert
    update_data = {
        'last_seen_at': datetime.datetime.now(datetime.timezone.utc),
        # We only update last_seen_at and add to sources_list if found again.
        # We keep the original scraped data ($setOnInsert handles this).
    }

    try:
        update_result = collection.update_one(
            {'primary_identifier': primary_id},
            {
                '$setOnInsert': insert_data,
                '$set': update_data,
                # Track all sources seen using $addToSet
                '$addToSet': {'sources_list': doc_to_store.get('source_platform')}
            },
            upsert=True
        )

        if update_result.upserted_id:
            logging.info(f"INSERTED new job: '{doc_to_store.get('job_title')}' ({doc_to_store.get('source_platform')}) | ID: {primary_id}")
            return True # Indicate new job inserted
        elif update_result.matched_count > 0:
            # Log that a duplicate was found, but don't log an error
            logging.info(f"DUPLICATE job found (already exists): '{doc_to_store.get('job_title')}' ({doc_to_store.get('source_platform')}) | ID: {primary_id}")
            # Update the sources_list even for duplicates
            collection.update_one(
                 {'primary_identifier': primary_id},
                 {'$addToSet': {'sources_list': doc_to_store.get('source_platform')}}
            )
            return False # Indicate it was a duplicate
        else:
             # This case means upsert=True but nothing happened (rare)
             logging.warning(f"Job upsert reported no match and no upsert: '{doc_to_store.get('job_title')}' | ID: {primary_id}")
             return False

    except pymongo.errors.DuplicateKeyError:
         # This might happen in rare race conditions if index creation is slow or multiple processes run
         logging.warning(f"DUPLICATE job found (via index race condition?): '{doc_to_store.get('job_title')}' | ID: {primary_id}")
         # Try to update sources_list anyway
         try:
              collection.update_one(
                   {'primary_identifier': primary_id},
                   {'$addToSet': {'sources_list': doc_to_store.get('source_platform')}}
              )
         except Exception as update_err:
              logging.error(f"Failed to update sources_list for duplicate {primary_id}: {update_err}")
         return False
    except Exception as e:
        # Log other MongoDB errors
        logging.error(f"Failed to store job '{doc_to_store.get('job_title')}' in MongoDB: {e}", exc_info=True)
        return False # Indicate failure

