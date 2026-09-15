from aiohttp import web

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    # केवल छोटा सा 'OK' Text भेजें ताकि Output Size एकदम नगण्य (Minimal) रहे
    return web.Response(text="Bot is running!", content_type="text/plain")

async def web_server():
    web_app = web.Application()
    web_app.add_routes(routes)
    return web_app

# server.py
