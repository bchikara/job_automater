from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017")

# Access the database and collection
db = client["job_agent_db"]
collection = db["jobs"]

# Define the query to keep
keep_query = {
    "status": "new",
    "application_url": {"$regex": "greenhouse"}
}

# Find documents to keep
docs_to_keep = list(collection.find(keep_query, {"_id": 1}))
ids_to_keep = [doc["_id"] for doc in docs_to_keep]

# Delete all documents that don't match the keep criteria
delete_result = collection.delete_many({
    "_id": {"$nin": ids_to_keep}
})

print(f"Deleted {delete_result.deleted_count} documents.")
