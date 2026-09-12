import re
from pyrogram import Client, filters
from config import Config
from database import db

def extract_episode_info(text):
    # 1. Range match (e.g., 1-10, 1 to 10, ep 1-10, e11-20)
    range_match = re.search(r'(?:ep|episode|e)?\s*(\d+)\s*(?:-|to)\s*(\d+)', text, re.IGNORECASE)
    if range_match:
        return f"{range_match.group(1)}-{range_match.group(2)}"
    
    # 2. Single Episode match (e.g., ep 11, e5, episode 02)
    single_match = re.search(r'(?:ep|episode|e)\s*(\d+)', text, re.IGNORECASE)
    if single_match:
        return single_match.group(1)

    # 3. Fallback for standalone numbers
    num_match = re.search(r'\b(\d{1,4})\b', text)
    if num_match:
        return num_match.group(1)
        
    return None

def parse_post_content(message):
    raw_text = message.caption or message.text or ""
    if not raw_text:
        return None, None, None

    # Inline Button se custom link check karna
    custom_link = None
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    custom_link = btn.url
                    break

    # Text URL extraction
    urls = re.findall(r'https?://[^\s]+', raw_text)
    if not custom_link and urls:
        custom_link = urls[0]

    if not custom_link:
        custom_link = message.link

    # Title ke liye sirf pehli line extract karna
    first_line = raw_text.split('\n')[0].strip()
    if "|" in first_line:
        title = first_line.split("|")[0].strip()
    else:
        title = re.sub(r'https?://[^\s]+', '', first_line).strip()

    episode_info = extract_episode_info(first_line)
    return title, custom_link, episode_info


# 1. CHANNEL AUTOMATIC INDEXING HANDLER
@Client.on_message(filters.channel & filters.chat(Config.INDEX_CHANNEL))
async def auto_index_handler(client, message):
    title, link, episode_info = parse_post_content(message)
    if not title or not link:
        return

    await db.save_post(title=title, link=link, episode_info=episode_info)


# 2. MANUAL INDEX COMMAND (/index)
@Client.on_message(filters.command("index") & filters.user(Config.OWNER_ID))
async def manual_index_command(client, message):
    target_msg = None

    if message.reply_to_message:
        target_msg = message.reply_to_message
    elif len(message.command) > 1:
        post_link = message.command[1]
        try:
            parts = post_link.split('/')
            msg_id = int(parts[-1])
            chat_id = parts[-2]
            chat_id = int("-100" + chat_id) if chat_id.isdigit() else f"@{chat_id}"
            target_msg = await client.get_messages(chat_id, msg_id)
        except Exception as e:
            await message.reply_text(f"❌ पोस्ट फेच करने में एरर आया: `{e}`")
            return

    if not target_msg:
        await message.reply_text(
            "⚠️ **उपयोग कैसे करें:**\n\n"
            "1️⃣ पोस्ट पर रिप्लाई करके `/index` लिखें।\n"
            "2️⃣ या कमांड दें: `/index <post_link>`"
        )
        return

    title, link, episode_info = parse_post_content(target_msg)
    if not title or not link:
        await message.reply_text("❌ इस पोस्ट से टाइटल या लिंक नहीं मिल सका।")
        return

    await db.save_post(title=title, link=link, episode_info=episode_info)
    ep_text = f" | EP: `{episode_info}`" if episode_info else ""
    await message.reply_text(f"✅ **इंडेक्स हो गया!**\n\n📌 **Title:** `{title}`\n🔗 **Link:** `{link}`{ep_text}")


# 3. INDEX LAST POST COMMAND (/index_last)
@Client.on_message(filters.command("index_last") & filters.user(Config.OWNER_ID))
async def index_last_post_command(client, message):
    try:
        async for last_msg in client.get_chat_history(Config.INDEX_CHANNEL, limit=1):
            title, link, episode_info = parse_post_content(last_msg)
            if not title or not link:
                await message.reply_text("❌ आखिरी पोस्ट से सही जानकारी नहीं मिली।")
                return

            await db.save_post(title=title, link=link, episode_info=episode_info)
            ep_text = f" | EP: `{episode_info}`" if episode_info else ""
            await message.reply_text(
                f"✅ **इंडेक्स चैनल की आखिरी पोस्ट इंडेक्स हो गई!**\n\n"
                f"📌 **Title:** `{title}`\n🔗 **Link:** `{link}`{ep_text}"
            )
            return
    except Exception as e:
        await message.reply_text(f"❌ एरर आया: `{e}`")
