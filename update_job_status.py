# update_job_status.py
# One-time script to set status='scraped' on existing jobs that are not already in a final/processing state.

import logging
import pymongo
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
MONGODB_CONNECTION_STRING = "mongodb://localhost:27017/"
DB_NAME = os.getenv('DB_NAME', "job_agent_db")
COLLECTION_NAME = "jobs" # Assuming your collection is named 'jobs'

# Define statuses that should NOT be reset to 'scraped'
FINAL_OR_PROCESSING_STATUSES = [
    'scraped', # Already correct
    # Add any other statuses you consider "don't touch"
]

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_existing_jobs():
    """Sets status='scraped' on documents where status is missing or not in a final/processing state."""
    client = None
    updated_count = 0
    try:
        logging.info(f"Connecting to MongoDB ({MONGODB_CONNECTION_STRING[:20]}...)")
        client = pymongo.MongoClient(MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster') # Verify connection
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        logging.info(f"Connected to DB: {DB_NAME}, Collection: {COLLECTION_NAME}")

        # Filter for documents where 'status' field either does not exist OR
        # its value is NOT one of the ones we want to preserve.
        filter_query = {
            'status': { '$nin': FINAL_OR_PROCESSING_STATUSES }
            # Using $nin handles cases where status is missing (null) or has an unwanted value.
        }
        # Alternatively, to explicitly include missing status:
        # filter_query = {
        #     '$or': [
        #         {'status': {'$exists': False}},
        #         {'status': {'$nin': FINAL_OR_PROCESSING_STATUSES}}
        #     ]
        # }
        # The $nin approach is generally sufficient.

        # Define the update operation to set status to 'scraped'
        update_operation = {'$set': {'status': 'scraped'}}

        logging.info(f"Attempting to update documents where status is not in {FINAL_OR_PROCESSING_STATUSES}...")
        # Perform the update_many operation
        result = collection.update_many(filter_query, update_operation)

        updated_count = result.modified_count
        logging.info(f"Update complete. Matched {result.matched_count} documents, Modified {updated_count} documents.")

    except pymongo.errors.ConnectionFailure as e:
        logging.error(f"MongoDB Connection Error: {e}")
    except Exception as e:
        logging.error(f"An error occurred during update: {e}", exc_info=True)
    finally:
        if client:
            client.close()
            logging.info("MongoDB connection closed.")
    return updated_count

if __name__ == "__main__":
    logging.info("Starting one-time status update script (Revised)...")
    count = update_existing_jobs()
    logging.info(f"Script finished. {count} documents were updated to status='scraped'.")

