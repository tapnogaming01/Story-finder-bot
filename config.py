
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", "123456"))
    API_HASH = os.environ.get("API_HASH", "your_api_hash")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://...")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "AutoFilterBot")
    INDEX_CHANNEL = int(os.environ.get("INDEX_CHANNEL", "-100123456789"))
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-100987654321"))  # Log Channel ID
    OWNER_ID = int(os.environ.get("OWNER_ID", "123456789"))
    REQ_CHANNEL = os.environ.get("REQ_CHANNEL", "")
    
    # ⬇️ यह नई लाइन जोड़ें (ADMINS list definition)
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "5898522531").split() if x.isdigit()]
    # config.py फ़ाइल में अपनी Sticker File ID डालें
    SEARCH_STICKER_ID = "CAACAgUAAxkBAAEBUAdqqTwpBKtnJUffWa0XeQABA5CchHsAAl4MAAKxjqhVi042_bzIzXEeBA" 
    
    
    REQUEST_MINI_APP_URL = "https://story-finder-bot-fjm9.onrender.com/request"
