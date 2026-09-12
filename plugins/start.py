from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from config import Config
from database import db

async def check_verification(client, user_id):
    if not Config.REQ_CHANNEL:
        return True
    try:
        sub = await client.get_chat_member(Config.REQ_CHANNEL, user_id)
        if sub.status in ["kicked", "banned"]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    # 1. Registration & Log Notification Check
    is_new_user = await db.add_user(user_id=user_id, first_name=first_name, username=username)
    
    if is_new_user and Config.LOG_CHANNEL:
        total_users = await db.total_users_count()
        log_text = (
            "🆕 **New User Joined!**\n\n"
            f"👤 **Name:** {first_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"🌐 **Username:** @{username if username else 'N/A'}\n\n"
            f"📊 **Total Users:** `{total_users}`"
        )
        try:
            await client.send_message(Config.LOG_CHANNEL, log_text)
        except Exception as e:
            print(f"Log Channel Error: {e}")

    # 2. Force Sub / Verification Check
    if not await check_verification(client, user_id):
        invite_link = f"https://t.me/{Config.REQ_CHANNEL}" if isinstance(Config.REQ_CHANNEL, str) else "https://t.me/"
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Verify / Try Again", url=f"https://t.me/{client.me.username}?start=start")]
        ])
        await message.reply_text(
            "⚠️ **सर्च करने से पहले आपको हमारे अपडेट चैनल को जॉइन करना होगा!**",
            reply_markup=btn
        )
        return

    text = message.text.split()
    if len(text) > 1:
        deep_param = text[1]
        await message.reply_text(f"आपने डीप-लिंक से स्टार्ट किया: **{deep_param}**")
        return

    welcome_text = (
        f"नमस्कार **{first_name}**!\n\n"
        "मैं एक एडवांस ऑटो-फिल्टर बॉट हूँ। मुझे ग्रुप में जोड़ें या यहाँ मैसेज लिखकर खोजें।"
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Owner", url=f"tg://user?id={Config.OWNER_ID}"),
            InlineKeyboardButton("About", callback_data="about_btn")
        ]
    ])
    
    await message.reply_text(welcome_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("about_btn"))
async def about_callback(client, query):
    await query.message.edit_text(
        "**About This Bot**\n\nयह बॉट ऑटोमैटिक चैनल पोस्ट्स को टाइटल और कस्टम लिंक्स के साथ इंडेक्स करता है।",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back_home")]])
    )

@Client.on_callback_query(filters.regex("back_home"))
async def back_home_callback(client, query):
    await start_handler(client, query.message)
