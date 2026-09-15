import motor.motor_asyncio
from datetime import datetime, timezone
from config import Config

class Database:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client[Config.DATABASE_NAME]
        self.posts = self.db.posts
        self.users = self.db.users
        self.settings = self.db.settings  # ⚙️ Admin Settings for Text vs Button layout

    # --- Upgraded Posts Logic (Story | Button Text | Link Support) ---
    async def save_post(self, caption_text):
        """
        फ़ॉर्मेट: "Story Name | Button Text | Link"
        उदाहरण: "My possessive saiyaan | My possessive saiyaan ep 1 To 10 | https://t.me/pratilipifm0900"
        """
        parts = [p.strip() for p in caption_text.split('|')]
        
        # अगर 3 पार्ट्स नहीं हैं तो प्रोसेस न करें
        if len(parts) < 3:
            return False

        story_name = parts[0]
        button_text = parts[1]
        link = parts[2]

        story_lower = story_name.lower()

        # Check duplicate button text or link in same story
        existing_doc = await self.posts.find_one({
            "story_lower": story_lower,
            "$or": [
                {"buttons.link": link},
                {"buttons.button_text": button_text}
            ]
        })

        if not existing_doc:
            # $push + $position: 0 से नया बटन लिस्ट में सबसे ऊपर (Top) ऐड होगा
            await self.posts.update_one(
                {"story_lower": story_lower},
                {
                    "$setOnInsert": {
                        "story_name": story_name,
                        "created_at": datetime.now(timezone.utc)
                    },
                    "$set": {
                        "story_lower": story_lower,
                        "updated_at": datetime.now(timezone.utc)
                    },
                    "$push": {
                        "buttons": {
                            "$each": [{
                                "button_text": button_text,
                                "link": link
                            }],
                            "$position": 0
                        }
                    }
                },
                upsert=True
            )
            return True
        return False

    # --- Suggestions / Did You Mean Logic ---
    async def get_story_suggestions(self, query):
        """
        यूज़र जब सर्च करेगा तो केवल UNIQUE Story Names के आधार पर रिजल्ट लाएगा
        """
        query_regex = {"$regex": query.strip(), "$options": "i"}
        cursor = self.posts.find(
            {"story_name": query_regex},
            {"story_name": 1, "buttons": 1}
        )
        return await cursor.to_list(length=None)

    async def get_all_story_names(self):
        """Fuzzy Matching के लिए सभी Unique Story Names निकालेगा"""
        return await self.posts.distinct("story_name")

    async def get_story_by_name(self, story_name):
        """जब यूज़र सजेशन वाले Story Button पर क्लिक करेगा, तो उसके सारे एपिसोड बटन्स निकालेगा"""
        return await self.posts.find_one({"story_lower": story_name.lower()})

    async def get_all_posts(self):
        cursor = self.posts.find({})
        return await cursor.to_list(length=None)

    # --- Delete Logic ---
    async def delete_story(self, story_name):
        """पूरी एक स्टोरी और उसके सभी बटन्स को डिलीट करेगा"""
        result = await self.posts.delete_one({"story_lower": story_name.lower()})
        return result.deleted_count > 0

    async def delete_button_from_story(self, story_name, button_text):
        """किसी विशिष्ट स्टोरी से केवल एक बटन/एपिसोड लिंक डिलीट करेगा"""
        result = await self.posts.update_one(
            {"story_lower": story_name.lower()},
            {"$pull": {"buttons": {"button_text": button_text}}}
        )
        return result.modified_count > 0

    async def drop_all_posts(self):
        """पूरे डेटाबेस संग्रह को खाली (Delete All) कर देगा"""
        await self.posts.delete_many({})
        return True

    # --- Global BOT Style Settings Logic ---
    async def get_bot_style(self):
        """
        बॉट का मौजूदा लेआउट स्टाइल (button या text) निकालेगा
        """
        config = await self.settings.find_one({"setting_id": "bot_layout"})
        if config and "layout_style" in config:
            return config["layout_style"]
        return "button"  # डिफ़ॉल्ट रूप से Button format रहेगा

    async def set_bot_style(self, style_name):
        """
        ऑनर के लिए रिस्पॉन्स स्टाइल (button / text) सेव या अपडेट करेगा
        """
        await self.settings.update_one(
            {"setting_id": "bot_layout"},
            {"$set": {"layout_style": style_name}},
            upsert=True
        )
        return True

    # --- User Registration Logic ---
    async def add_user(self, user_id, first_name, username=None):
        """अगर यूजर नया है तो रजिस्ट्रेशन करके True देगा, अगर पुराना है तो False देगा"""
        user = await self.users.find_one({"user_id": user_id})
        if not user:
            user_data = {
                "user_id": user_id,
                "first_name": first_name,
                "username": username,
                "joined_at": datetime.now(timezone.utc)
            }
            await self.users.insert_one(user_data)
            return True
        return False

    async def total_users_count(self):
        return await self.users.count_documents({})

db = Database()
