import motor.motor_asyncio
from datetime import datetime
from config import Config

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client[Config.DATABASE_NAME]
        self.posts = self.db.posts
        self.users = self.db.users

    # --- Posts Logic (Multiple Buttons & Links Support) ---
    async def save_post(self, title, link, button_name=None):
        """
        एक ही Story Title के अंदर मल्टीपल बटन और लिंक्स को सेव करता है।
        अगर लिंक या बटन पहले से मौजूद है, तो डुप्लीकेट होने से रोकता है।
        """
        clean_title = title.strip()
        title_lower = clean_title.lower()
        clean_button = button_name.strip() if button_name else "Open Link"
        clean_link = link.strip()

        # Check karein ki kya ye same link ya same button name pehle se iss title me hai
        existing_doc = await self.posts.find_one({
            "title_lower": title_lower,
            "$or": [
                {"links.link": clean_link},
                {"links.button_name": clean_button}
            ]
        })

        if not existing_doc:
            # Naya button aur link hai to same Story Title document me $push karein
            await self.posts.update_one(
                {"title_lower": title_lower},
                {
                    "$set": {
                        "title": clean_title,
                        "updated_at": datetime.utcnow()
                    },
                    "$push": {
                        "links": {
                            "button_name": clean_button,
                            "link": clean_link
                        }
                    }
                },
                upsert=True
            )

    async def get_all_posts(self):
        cursor = self.posts.find({})
        return await cursor.to_list(length=None)

    # --- User Registration Logic ---
    async def add_user(self, user_id, first_name, username=None):
        user = await self.users.find_one({"user_id": user_id})
        if not user:
            user_data = {
                "user_id": user_id,
                "first_name": first_name,
                "username": username,
                "joined_at": datetime.utcnow()
            }
            await self.users.insert_one(user_data)
            return True  # New User Registered
        return False  # Already Exists

    async def total_users_count(self):
        return await self.users.count_documents({})

db = Database()
