import asyncio
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
            await client.send_message(chat_id=int(Config.LOG_CHANNEL), text=log_text)
        except Exception as e:
            print(f"Log Channel Error: {e}")

    # 2. Force Sub / Verification Check
    if not await check_verification(client, user_id):
        req_channel = str(Config.REQ_CHANNEL).replace("-100", "")
        invite_link = f"https://t.me/{Config.REQ_CHANNEL}" if not req_channel.isdigit() else f"https://t.me/c/{req_channel}/1"
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Verify / Try Again", url=f"https://t.me/{client.me.username}?start=start")]
        ])
        await message.reply_text(
            "⚠️ **Access Denied!**\n\n"
            "ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴛʜɪs ʙᴏᴛ.",
            reply_markup=btn
        )
        return

    text = message.text.split()
    if len(text) > 1:
        deep_param = text[1]
        await message.reply_text(f"🚀 **Started via Deep-Link:** `{deep_param}`")
        return

    # Main Home UI
    welcome_text = (
        f"👋 **ʜᴇʏ {first_name}!**\n\n"
        "ɪ ᴀᴍ **ɪɴғɪɴɪᴛʏ sᴛᴏʀʏs ғɪɴᴅᴇʀ ʙᴏᴛ**, ᴛʜᴇ ᴍᴏsᴛ ᴘᴏᴡᴇʀғᴜʟ ᴀɴᴅ ᴀᴜᴛᴏᴍᴀᴛᴇᴅ "
        "ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ sᴇᴀʀᴄʜ ᴇɴɢɪɴᴇ.\n\n"
        "✨ *ᴊᴜsᴛ sᴇɴᴅ ᴍᴇ ᴛʜᴇ ɴᴀᴍᴇ ᴏғ ᴀɴʏ sᴛᴏʀʏ ᴏʀ ᴇᴘɪsᴏᴅᴇ ᴛᴏ sᴇᴀʀᴄʜ!*"
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👨‍💻 Developer", url=f"tg://user?id={Config.OWNER_ID}"),
            InlineKeyboardButton("ℹ️ About", callback_data="about_btn")
        ]
    ])
    
    await message.reply_text(welcome_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("about_btn"))
async def about_callback(client, query):
    about_text = (
        "🤖 **ᴀʙᴏᴜᴛ ᴛʜɪs ʙᴏᴛ**\n\n"
        "▸ **ɴᴀᴍᴇ:** ɪɴғɪɴɪᴛʏ sᴛᴏʀʏs ғɪɴᴅᴇʀ ʙᴏᴛ\n"
        "▸ **ғᴜɴᴄᴛɪᴏɴ:** ᴀᴜᴛᴏ-ɪɴᴅᴇx & ғᴜᴢᴢʏ sᴇᴀʀᴄʜ ᴇɴɢɪɴᴇ\n"
        "▸ **ᴅᴇᴠᴇʟᴏᴘᴇʀ:** [Kaluu](tg://user?id=" + str(Config.OWNER_ID) + ")\n"
        "▸ **ʟᴀɴɢᴜᴀɢᴇ:** Python 3\n"
        "▸ **ғʀᴀᴍᴇᴡᴏʀᴋ:** kurigram v2.2.25"
    )
    await query.message.edit_text(
        about_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_home")]])
    )

@Client.on_callback_query(filters.regex("back_home"))
async def back_home_callback(client, query):
    first_name = query.from_user.first_name
    
    welcome_text = (
        f"👋 **ʜᴇʏ {first_name}!**\n\n"
        "ɪ ᴀᴍ **ɪɴғɪɴɪᴛʏ sᴛᴏʀʏs ғɪɴᴅᴇʀ ʙᴏᴛ**, ᴛʜᴇ ᴍᴏsᴛ ᴘᴏᴡᴇʀғᴜʟ ᴀɴᴅ ᴀᴜᴛᴏᴍᴀᴛᴇᴅ "
        "ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ sᴇᴀʀᴄʜ ᴇɴɢɪɴᴇ.\n\n"
        "✨ *ᴊᴜsᴛ sᴇɴᴅ ᴍᴇ ᴛʜᴇ ɴᴀᴍᴇ ᴏғ ᴀɴʏ sᴛᴏʀʏ ᴏʀ ᴇᴘɪsᴏᴅᴇ ᴛᴏ sᴇᴀʀᴄʜ!*"
    )
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👨‍💻 Developer", url=f"tg://user?id={Config.OWNER_ID}"),
            InlineKeyboardButton("ℹ️ About", callback_data="about_btn")
        ]
    ])
    
    # Back click par direct message edit hoga (Deep-link issue fixed)
    await query.message.edit_text(welcome_text, reply_markup=buttons)
