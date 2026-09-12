import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db

WAITING_INDEX_LINK = {}

def parse_post_content(message):
    """
    पोस्ट की पहली लाइन को Story Title मानकर
    Button Name और Link निकालता है।
    """
    raw_text = message.caption or message.text or ""
    if not raw_text:
        return None, None, None

    # Line 1 -> Story Title
    lines = raw_text.strip().split('\n')
    first_line = lines[0].strip()

    # Format 1: Title | Button Name | Link
    if "|" in first_line:
        parts = [p.strip() for p in first_line.split("|")]
        title = parts[0]
        button_name = parts[1] if len(parts) > 1 else "Open Link"
        link = parts[2] if len(parts) > 2 else None
    else:
        title = first_line
        button_name = "Open Link"
        link = None

    # Inline Button se Link check karna (agar text me link na mile)
    if not link and message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    link = btn.url
                    if btn.text and button_name == "Open Link":
                        button_name = btn.text
                    break

    # Text URL extraction (Fallback)
    if not link:
        urls = re.findall(r'https?://[^\s]+', raw_text)
        if urls:
            link = urls[0]

    # Agar koi direct URL nahi mila to Telegram post link use hoga
    if not link:
        chat_id_str = str(message.chat.id).replace("-100", "")
        link = f"https://t.me/c/{chat_id_str}/{message.id}"

    return title, button_name, link


# 1. 🤖 REAL-TIME AUTO INDEXING (चैनल में पोस्ट डालते ही Auto-Save)
@Client.on_message(filters.channel & filters.chat(Config.INDEX_CHANNEL))
async def auto_index_handler(client, message):
    title, button_name, link = parse_post_content(message)
    if not title or not link:
        return

    await db.save_post(title=title, link=link, button_name=button_name)
    print(f"✅ Auto-Indexed: {title} -> {button_name}")


# 2. 🔄 MANUAL INDEX COMMAND (/index -> Prompts for Last Link)
@Client.on_message(filters.command("index") & filters.private & filters.user(Config.OWNER_ID))
async def manual_index_command(client, message):
    user_id = message.from_user.id
    WAITING_INDEX_LINK[user_id] = True
    await message.reply_text(
        "📥 **Now send last link in your database channel.**\n\n"
        "*(For example: `https://t.me/c/123456789/500` or `https://t.me/your_channel/500`)*"
    )


# 3. 🔍 CHANNEL REFRESHER HANDLER (Link मिलने पर पूरे चैनल को स्कैन करके Refresh करेगा)
@Client.on_message(filters.text & filters.private & filters.user(Config.OWNER_ID))
async def handle_channel_link_indexing(client, message):
    user_id = message.from_user.id
    if not WAITING_INDEX_LINK.get(user_id):
        return

    text = message.text.strip()
    link_pattern = r"https://t\.me/(?:c/(\d+)|([a-zA-Z0-9_]+))/(\d+)"
    match = re.search(link_pattern, text)

    if not match:
        await message.reply_text("❌ **Invalid Telegram Link!**\nPlease send a valid post link from your database channel.")
        return

    WAITING_INDEX_LINK[user_id] = False

    channel_identifier = match.group(1) or match.group(2)
    last_msg_id = int(match.group(3))

    target_chat = int(f"-100{channel_identifier}") if match.group(1) else channel_identifier
    status_msg = await message.reply_text(f"⏳ **Refreshing database... Scanning messages up to ID `{last_msg_id}`**")

    saved_count = 0
    skipped_count = 0

    # Retrieve existing links to prevent duplicates
    existing_posts = await db.get_all_posts()
    existing_links = set()
    for post in existing_posts:
        for l in post.get("links", []):
            existing_links.add(l.get("link"))

    for msg_id in range(1, last_msg_id + 1):
        try:
            msg = await client.get_messages(target_chat, msg_id)
            if not msg or msg.empty:
                continue

            title, button_name, link = parse_post_content(msg)

            if link in existing_links:
                skipped_count += 1
                continue

            if title and link:
                await db.save_post(title=title, link=link, button_name=button_name)
                saved_count += 1
                existing_links.add(link)

        except Exception:
            continue

        if msg_id % 20 == 0:
            try:
                await status_msg.edit_text(
                    f"🔄 **Indexing Progress...**\n\n"
                    f"🔢 Message ID: `{msg_id}/{last_msg_id}`\n"
                    f"✅ Saved: `{saved_count}`\n"
                    f"⏩ Skipped (Already Exist): `{skipped_count}`"
                )
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ **Database Channel Indexing Completed!**\n\n"
        f"📊 **Total Scanned:** `{last_msg_id}`\n"
        f"🆕 **New Saved:** `{saved_count}`\n"
        f"⏩ **Skipped (Already Saved):** `{skipped_count}`"
    )
