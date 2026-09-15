import os
from aiohttp import web

routes = web.RouteTableDef()

# 1. Uptime / Ping Route (Render / Health Check के लिए)
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text="Bot is running!", content_type="text/plain")

# 2. Mini App Route (यहाँ से HTML ఫార్మ్ लोड होगा)
@routes.get("/request", allow_head=True)
async def mini_app_route_handler(request):
    # यह web/index.html फ़ाइल को Telegram Mini App के रूप में लोड करेगा
    if os.path.exists("./web/index.html"):
        return web.FileResponse("./web/index.html")
    return web.Response(text="index.html file not found in /web directory!", status=444)

async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app
