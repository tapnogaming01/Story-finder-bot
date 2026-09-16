import os
import json
from aiohttp import web
from config import Config

routes = web.RouteTableDef()

# 1. Uptime / Ping Route (Render / Health Check के लिए)
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text="Bot is running!", content_type="text/plain")

# 2. Mini App Route (यहाँ से HTML फ़ॉर्म लोड होगा)
@routes.get("/request", allow_head=True)
async def mini_app_route_handler(request):
    if os.path.exists("./web/index.html"):
        return web.FileResponse("./web/index.html")
    return web.Response(text="index.html file not found in /web directory!", status=444)

# 3. API Route (जो index.html से आने वाले POST रिक्वेस्ट को रिसीव करेगा)
@routes.post("/api/request_story")
async def request_story_handler(request):
    try:
        data = await request.json()
        story_name = data.get("story_name", "N/A")
        details = data.get("details", "N/A")
        user_id = data.get("user_id", "Unknown")
        first_name = data.get("first_name", "User")
        username = data.get("username", "None")

        print(f"📩 New Request Received: {story_name} from {first_name} ({user_id})")

        # 200 OK रिस्पॉन्स वापस index.html को भेजें
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

async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app
