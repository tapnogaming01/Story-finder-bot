import re
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from config import Config
from database import db

def parse_post_content(message):
    raw_text = message.caption or message.text or ""
    
    # 1. Inline Buttons से Link और Text निकालने का प्रयास करें
    buttons_found = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    buttons_found.append((btn.text, btn.url))

    if not raw_text and not buttons_found:
        return None

    # केवल पहली लाइन लें
    first_line = raw_text.split('\n')[0].strip() if raw_text else ""

    custom_link = buttons_found[0][1] if buttons_found else None

    urls = re.findall(r'https?://[^\s]+', first_line or raw_text)
    if not custom_link and urls:
        custom_link = urls[0]

    if not custom_link:
        custom_link = message.link

    # 2. Split by Pipe (|) Symbol
    parts = [p.strip() for p in first_line.split('|')] if first_line else []

    # केस 1: "Story Name | Button Text | Link" (3 or more parts)
    if len(parts) >= 3:
        story_name = parts[0]
        button_text = parts[1]
        link = parts[2]
        
        if not link.startswith("http"):
            link = custom_link

    # केस 2: "Story Name | Button Text" (2 parts - link auto fetch)
    elif len(parts) == 2:
        story_name = parts[0]
        button_text = parts[1]
        link = custom_link

    # केस 3: Inline Keyboard Present or Legacy Format
    else:
        clean_text = re.sub(r'https?://[^\s]+', '', first_line).strip()
        story_name = clean_text if clean_text else "Untitled Story"
        
        if buttons_found:
            button_text = buttons_found[0][0]
            link = buttons_found[0][1]
        else:
            button_text = clean_text
            link = custom_link

    if not story_name or not button_text or not link:
        return None

    caption_format = f"{story_name} | {button_text} | {link}"
    return caption_format, story_name, button_text, link


# 1. CHANNEL AUTOMATIC INDEXING HANDLER
@Client.on_message(filters.channel & filters.chat(Config.INDEX_CHANNEL))
async def auto_index_handler(client, message):
    parsed_data = parse_post_content(message)
    if not parsed_data:
        return

    caption_format, story_name, button_text, link = parsed_data
    await db.save_post(caption_text=caption_format)


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

    parsed_data = parse_post_content(target_msg)
    if not parsed_data:
        await message.reply_text("❌ इस पोस्ट से स्टोरी का नाम, बटन टेक्स्ट या लिंक नहीं मिल सका।")
        return

    caption_format, story_name, button_text, link = parsed_data
    success = await db.save_post(caption_text=caption_format)
    
    if success:
        await message.reply_text(
            f"✅ **इंडेक्स हो गया!**\n\n"
            f"📖 **Story Name:** `{story_name}`\n"
            f"🔘 **Button Text:** `{button_text}`\n"
            f"🔗 **Link:** `{link}`"
        )
    else:
        await message.reply_text("⚠️ यह बटन या लिंक पहले से इस स्टोरी में मौजूद है।")


# 3. INDEX LAST POST COMMAND (/index_last) - FIXED (Bot Compatible)
@Client.on_message(filters.command("index_last") & filters.user(Config.OWNER_ID))
async def index_last_post_command(client, message):
    try:
        # चैनल में एक डमी मैसेज भेजकर सबसे लेटेस्ट Message ID निकालें
        temp_msg = await client.send_message(Config.INDEX_CHANNEL, ".")
        last_id = temp_msg.id
        await temp_msg.delete()

        # बैकवर्ड लूप से आखिरी असली पोस्ट निकालें (get_chat_history हटा दिया गया है)
        last_msg = None
        for check_id in range(last_id - 1, max(1, last_id - 15), -1):
            try:
                msg = await client.get_messages(Config.INDEX_CHANNEL, check_id)
                if msg and not msg.empty and (msg.text or msg.caption or msg.reply_markup):
                    last_msg = msg
                    break
            except Exception:
                continue

        if not last_msg:
            await message.reply_text("❌ इंडेक्स चैनल में कोई पोस्ट नहीं मिली।")
            return

        parsed_data = parse_post_content(last_msg)
        if not parsed_data:
            await message.reply_text("❌ आखिरी पोस्ट से सही जानकारी नहीं मिली।")
            return

        caption_format, story_name, button_text, link = parsed_data
        await db.save_post(caption_text=caption_format)
        
        await message.reply_text(
            f"✅ **इंडेक्स चैनल की आखिरी पोस्ट इंडेक्स हो गई!**\n\n"
            f"📖 **Story Name:** `{story_name}`\n"
            f"🔘 **Button Text:** `{button_text}`\n"
            f"🔗 **Link:** `{link}`"
        )

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        await message.reply_text(f"❌ एरर आया: `{e}`")
