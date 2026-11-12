"""
test_mongo_connection.py
------------------------
Utility script to test MongoDB Atlas connectivity.
Credentials are read securely from backend/.env and never printed.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.mongo import ping_mongodb
from app.config import settings

async def main():
    print("Testing connection to MongoDB Atlas...")
    if not settings.MONGODB_URL:
        print("[!] MONGODB_URL is not set in backend/.env.")
        print("[!] Please open backend/.env and paste your connection string:")
        print('    MONGODB_URL="mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority"')
        print('    MONGODB_DB_NAME="mindtrace"')
        return

    result = await ping_mongodb()
    if result["success"]:
        print(f"[SUCCESS] {result['message']}")
        print(f"Target Database: {result.get('database')}")
    else:
        print(f"[FAILED] {result['message']}")

if __name__ == "__main__":
    asyncio.run(main())

