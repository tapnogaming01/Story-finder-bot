import motor.motor_asyncio
from datetime import datetime
from config import Config

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client[Config.DATABASE_NAME]
        self.posts = self.db.posts
        self.users = self.db.users

    # --- Posts Logic (Multiple Links & Ranges Support) ---
    async def save_post(self, title, link, episode_info=None):
        """
        एक ही टाइटल के अंदर multiple links और episode ranges (जैसे '1-10', '11-20', '5') 
        को डेटाबेस में सुरक्िषत सेव करता है बिना पुराना डेटा डिलीट किए।
        """
        clean_title = title.strip()
        title_lower = clean_title.lower()

        # Check karein ki kya ye link pehle se iss title me hai
        existing_doc = await self.posts.find_one({
            "title_lower": title_lower,
            "links.link": link
        })

        if not existing_doc:
            # Agar new link hai to $push karein
            await self.posts.update_one(
                {"title_lower": title_lower},
                {
                    "$set": {
                        "title": clean_title,
                        "updated_at": datetime.utcnow()
                    },
                    "$push": {
                        "links": {
                            "link": link,
                            "episode_info": str(episode_info) if episode_info else None
                        }
                    }
                },
                upsert=True
            )

    async def search_posts(self, query):
        """Fuzzy/Regex Search for Title Match"""
        query_regex = {"$regex": query.strip(), "$options": "i"}
        cursor = self.posts.find({"title": query_regex})
        return await cursor.to_list(length=None)

    async def get_all_posts(self):
        cursor = self.posts.find({})
        return await cursor.to_list(length=None)

    # --- User Registration Logic ---
    async def add_user(self, user_id, first_name, username=None):
        """अगर यूजर नया है तो रजिस्ट्रेशन करके True देगा, अगर पुराना है तो False देगा"""
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
