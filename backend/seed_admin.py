import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from models import gen_id, now_iso
from auth import hash_password

async def seed_admin():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    print(f"Connecting to MongoDB database '{db_name}'...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    email = "admin@msme.com"
    password = "admin123"
    
    existing = await db.users.find_one({"email": email})
    if existing:
        print(f"User {email} already exists!")
        # Let's update the password just in case it was different
        await db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": hash_password(password)}}
        )
        print("Updated password successfully!")
    else:
        user_id = gen_id()
        doc = {
            "id": user_id,
            "email": email,
            "name": "Admin User",
            "role": "admin",
            "password_hash": hash_password(password),
            "created_at": now_iso(),
        }
        await db.users.insert_one(doc)
        print(f"Created admin user: {email} with ID: {user_id}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_admin())
