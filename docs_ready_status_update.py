from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017")

# Access the database and collection
db = client["job_agent_db"]
collection = db["jobs"]

# Update all documents: set status to "docs_ready"
update_result = collection.update_many({}, {"$set": {"status": "new"}})

print(f"Updated {update_result.modified_count} documents to status 'docs_ready'.")
