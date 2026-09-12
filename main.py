import os
from pyrogram import Client
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

    # Log Channel Restart Alert Send Logic
    if Config.LOG_CHANNEL:
        try:
            bot_info = await app.get_me()
            await app.send_message(
                Config.LOG_CHANNEL,
                f"🤖 **Bot Restarted Successfully!**\n\n"
                f"🔹 **Name:** {bot_info.first_name}\n"
                f"🔹 **Username:** @{bot_info.username}\n"
                f"🚀 **Status:** Active & Ready!"
            )
        except Exception as e:
            print(f"Failed to send restart message to Log Channel: {e}")

    # Render Port Listener Start
    PORT = int(os.environ.get("PORT", 8080))
    server = web.AppRunner(await web_server())
    await server.setup()
    site = web.TCPSite(server, "0.0.0.0", PORT)
    await site.start()
    print(f"Web Server running on port {PORT}")

    await app.idle()

if __name__ == "__main__":
    app.run(start_services())
