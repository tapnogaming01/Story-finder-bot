import os
import json
from aiohttp import web
from config import Config

routes = web.RouteTableDef()

# 1. Uptime / Ping Route
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text="Bot is running!", content_type="text/plain")

# 2. Mini App Route
@routes.get("/request", allow_head=True)
async def mini_app_route_handler(request):
    if os.path.exists("./web/index.html"):
        return web.FileResponse("./web/index.html")
    return web.Response(text="index.html file not found in /web directory!", status=444)

# 3. API Route (जो लॉग चैनल में मैसेज भेजेगा)
@routes.post("/api/request_story")
async def request_story_handler(request):
    try:
        data = await request.json()
        story_name = data.get("story_name", "N/A")
        details = data.get("details", "N/A")
        user_id = data.get("user_id", "Unknown")
        first_name = data.get("first_name", "User")
        username = data.get("username", "None")

        # Pyrogram Bot Client को एप से प्राप्त करें
        bot = request.app.get("bot_client")

        # LOG CHANNEL में संदेश भेजें
        if bot and getattr(Config, "LOG_CHANNEL", None):
            log_text = (
                "📥 **ɴᴇᴡ sᴛᴏʀʏ ʀᴇǫᴜᴇsᴛ (ᴍɪɴɪ ᴀᴘᴘ)**\n\n"
                f"👤 **Name:** {first_name}\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"🌐 **Username:** {username}\n\n"
                f"📖 **Story Name:** `{story_name}`\n"
                f"📝 **Details:** `{details}`"
            )
            try:
                await bot.send_message(chat_id=int(Config.LOG_CHANNEL), text=log_text)
            except Exception as log_err:
                print(f"❌ Log Channel Error: {log_err}")

        return web.json_response({
            "status": "success",
            "message": "Request submitted successfully!"
        }, status=200)

    except Exception as e:
        print(f"❌ API Request Error: {e}")
        return web.json_response({
            "status": "error",
            "message": "Internal Server Error"
        }, status=500)

async def web_server(bot_client=None):
    web_app = web.Application()
    if bot_client:
        web_app["bot_client"] = bot_client
    web_app.add_routes(routes)
    return web_app
