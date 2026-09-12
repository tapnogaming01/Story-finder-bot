import os
import asyncio
from pyrogram import Client, idle
from config import Config
from aiohttp import web
from server import web_server

app = Client(
    "AutoFilterBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="plugins")
)

async def start_services():
    print("Bot Starting...")
    await app.start()

    # Restart Notification
    if Config.LOG_CHANNEL:
        try:
            bot_info = await app.get_me()
            await app.send_message(
                chat_id=int(Config.LOG_CHANNEL),
                text=f"🤖 **Bot Restarted Successfully!**\n\n"
                     f"🔹 **Name:** {bot_info.first_name}\n"
                     f"🔹 **Username:** @{bot_info.username}\n"
                     f"🚀 **Status:** Active & Ready!"
            )
            print("LOG: Restart message sent to Log Channel successfully!")
        except Exception as e:
            print(f"ERROR (Restart Alert): {e}")

    # Render Port Listener
    PORT = int(os.environ.get("PORT", 8080))
    server = web.AppRunner(await web_server())
    await server.setup()
    site = web.TCPSite(server, "0.0.0.0", PORT)
    await site.start()
    print(f"Web Server running on port {PORT}")

    await idle()
    await app.stop()

if __name__ == "__main__":
    # Correct way to run async main loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
