import re
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import ForceReply
from config import Config
from database import db

# ग्लोबल वेरिएबल जो यह ट्रैक रखेगा कि क्या स्कैनिंग अभी चल रही है
IS_INDEXING = False

def parse_post_content(message):
    raw_text = message.caption or message.text or ""
    
    # Inline Buttons से Link और Text निकालें
    buttons_found = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    buttons_found.append((btn.text, btn.url))

    if not raw_text and not buttons_found:
        return None

    # केवल पहली लाइन लें (Story Title के लिए)
    first_line = raw_text.split('\n')[0].strip() if raw_text else ""
    parts = [p.strip() for p in first_line.split('|')] if first_line else []
    
    if parts and parts[0]:
        story_name = parts[0]
    else:
        clean_text = re.sub(r'https?://[^\s]+', '', first_line).strip()
        story_name = clean_text if clean_text else "Untitled Story"

    if buttons_found:
        return story_name, buttons_found

    custom_link = message.link
    urls = re.findall(r'https?://[^\s]+', first_line or raw_text)
    if urls:
        custom_link = urls[0]

    if len(parts) >= 3:
        button_text = parts[1]
        link = parts[2] if parts[2].startswith("http") else custom_link
    elif len(parts) == 2:
        button_text = parts[1]
        link = custom_link
    else:
        button_text = story_name
        link = custom_link

    return story_name, [(button_text, link)]


# 1. /index COMMAND - लास्ट पोस्ट लिंक की माँग करेगा
@Client.on_message(filters.command("index") & filters.user(Config.OWNER_ID))
async def manual_index_command(client, message):
    global IS_INDEXING
    if IS_INDEXING:
        await message.reply_text("⚠️ **इंडेक्सिंग पहले से चल रही है!** कृपया इसके पूरा होने का इंतज़ार करें।")
        return

    await message.reply_text(
        "👇 **चैनल की आखिरी (Latest) पोस्ट का लिंक भेजें:**\n\n"
        "*(बोट मैसेज ID 1 से लेकर इस लास्ट लिंक तक की पूरी पोस्ट्स को स्कैन करेगा)*",
        reply_markup=ForceReply(True)
    )


# 2. LINK LISTENER - जब भी आप Telegram Post Link भेजेंगे (रिप्लाई हो या डायरेक्ट)
@Client.on_message(filters.private & filters.text & filters.user(Config.OWNER_ID) & ~filters.command(["index", "start", "help"]))
async def start_full_channel_index(client, message):
    global IS_INDEXING

    # टेक्स्ट में टेलीग्राम का पोस्ट लिंक तलाशें
    urls = re.findall(r'https?://t\.me/[^\s]+', message.text)
    if not urls:
        return

    if IS_INDEXING:
        await message.reply_text("⚠️ **इंडेक्सिंग पहले से चालू है!** कृपया पुरानी प्रोसेस खत्म होने दें।")
        return

    # लिंक पार्स करके Channel ID और Message ID निकालें
    try:
        parts = urls[0].split('/')
        last_msg_id = int(parts[-1])
        chat_id = parts[-2]
        chat_id = int("-100" + chat_id) if chat_id.isdigit() else f"@{chat_id}"
    except Exception as e:
        await message.reply_text(f"❌ लिंक पार्स करने में एरर आया: `{e}`")
        return

    IS_INDEXING = True
    status_msg = await message.reply_text(
        f"⏳ **पूरे चैनल की इंडेक्सिंग शुरू हो रही है...**\n\n"
        f"🎯 **Target Last Message ID:** `{last_msg_id}`\n"
        f"📢 **Channel:** `{chat_id}`"
    )

    total_scanned = 0
    saved_count = 0
    skipped_count = 0

    # Message ID 1 से लेकर Last Message ID तक लूप चलाएँ
    for msg_id in range(1, last_msg_id + 1):
        try:
            target_msg = await client.get_messages(chat_id, msg_id)
            
            if not target_msg or target_msg.empty:
                continue

            parsed_data = parse_post_content(target_msg)
            if not parsed_data:
                continue

            story_name, buttons = parsed_data
            for btn_text, btn_link in buttons:
                total_scanned += 1
                caption_format = f"{story_name} | {btn_text} | {btn_link}"
                success = await db.save_post(caption_text=caption_format)
                
                if success:
                    saved_count += 1
                else:
                    skipped_count += 1

            # हर 20 मैसेज पर लाइव प्रोग्रेस अपडेट दिखाएगा
            if msg_id % 20 == 0:
                await status_msg.edit_text(
                    f"🔄 **चैनल स्कैनिंग प्रगति पर है...**\n\n"
                    f"🔹 **प्रगति:** `{msg_id}/{last_msg_id}` Messages\n"
                    f"➕ **नए जुड़े:** `{saved_count}`\n"
                    f"⚠️ **Skipped (पहले से मौजूद):** `{skipped_count}`"
                )
            
            await asyncio.sleep(0.4)

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            continue

    IS_INDEXING = False
    await status_msg.edit_text(
        f"✅ **पूरे चैनल की इंडेक्सिंग समाप्त हो गई!**\n\n"
        f"📊 **कुल मैसेज स्कैन किए गए:** `{last_msg_id}`\n"
        f"🔘 **कुल बटन्स स्कैन हुए:** `{total_scanned}`\n"
        f"➕ **नये डेटाबेस में जुड़े:** `{saved_count}`\n"
        f"⚠️ **पुराने (Skipped):** `{skipped_count}`"
    )
