import re
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserIsBlocked, PeerIdInvalid
from config import Config
from database import db

# -----------------------------------------------------------------------------
# 🔹 METHOD 1: रिक्वेस्ट करने वाले यूज़र्स को नोटीफाई करें (Requesters)
# -----------------------------------------------------------------------------
async def notify_request_users(client, story_name):
    """
    जब कोई नई स्टोरी अपलोड होगी, तो यह फ़ंक्शन सिर्फ उन यूज़र्स को 
    नोटीफाई करेगा जिन्होंने Mini App/Form से इसकी रिक्वेस्ट की थी।
    """
    try:
        # Request Collection से यूज़र्स निकालें
        req_doc = await db.db.requests.find_one({"story_name": story_name})
        if not req_doc or "user_ids" not in req_doc or not req_doc["user_ids"]:
            return

        user_ids = req_doc["user_ids"]

        notification_text = (
            f"🎉 **ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ɪs ᴀᴘᴘʀᴏᴠᴇᴅ!**\n\n"
            f"📖 **sᴛᴏʀʏ:** `{story_name}`\n\n"
            f"✨ आपने जिस स्टोरी की रिक्वेस्ट की थी, वह अब बोट में अपलोड कर दी गई है!\n\n"
            f"🔍 अभी बोट में `{story_name}` लिखकर सर्च करें और डाउनलोड करें।"
        )

        for user_id in user_ids:
            try:
                await client.send_message(chat_id=user_id, text=notification_text)
                await asyncio.sleep(0.1)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await client.send_message(chat_id=user_id, text=notification_text)
                except Exception:
                    pass
            except (UserIsBlocked, PeerIdInvalid, Exception):
                pass

        # रिक्वेस्ट पूरी होने के बाद डेटाबेस से इस रिक्वेस्ट को डिलीट/क्लियर कर दें
        await db.db.requests.delete_one({"story_name": story_name})

    except Exception as e:
        print(f"Error in notify_request_users: {e}")


# -----------------------------------------------------------------------------
# 🔹 METHOD 2: सब्सक्राइब करने वाले यूज़र्स को नोटीफाई करें (Subscribers)
# -----------------------------------------------------------------------------
async def notify_subscribers(client, story_name):
    """
    जब स्टोरी में नया एपिसोड/अपडेट आएगा, तो यह फ़ंक्शन सिर्फ उन यूज़र्स को 
    नोटीफाई करेगा जिन्होंने 'Subscribe Updates' बटन दबाया था।
    """
    try:
        # Subscriber Collection से यूज़र्स निकालें
        sub_doc = await db.db.subscribers.find_one({"story_name": story_name})
        if not sub_doc or "user_ids" not in sub_doc or not sub_doc["user_ids"]:
            return

        user_ids = sub_doc["user_ids"]

        notification_text = (
            f"🔔 **ɴᴇᴡ ᴇᴘɪsᴏᴅᴇ / ᴜᴘᴅᴀᴛᴇ ᴀᴠᴀɪʟᴀʙʟᴇ!**\n\n"
            f"📖 **sᴛᴏʀʏ:** `{story_name}`\n\n"
            f"✨ आपकी पसंदीदा स्टोरी में नया एपिसोड / कंटेंट जोड़ दिया गया है!\n\n"
            f"🔍 बोट में `{story_name}` लिखकर सर्च करें और नए एपिसोड्स देखें।"
        )

        for user_id in user_ids:
            try:
                await client.send_message(chat_id=user_id, text=notification_text)
                await asyncio.sleep(0.1)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await client.send_message(chat_id=user_id, text=notification_text)
                except Exception:
                    pass
            except (UserIsBlocked, PeerIdInvalid, Exception):
                pass

    except Exception as e:
        print(f"Error in notify_subscribers: {e}")


# -----------------------------------------------------------------------------
# 🔹 HELPER: दोनों मेथड्स को एक साथ ट्रिगर करने के लिए मास्टर फ़ंक्शन
# -----------------------------------------------------------------------------
async def trigger_all_notifications(client, story_name):
    # 1. रिक्वेस्ट करने वाले यूज़र्स को मैसेज भेजें
    await notify_request_users(client, story_name)
    # 2. सब्सक्राइब करने वाले यूज़र्स को मैसेज भेजें
    await notify_subscribers(client, story_name)


def parse_post_content(message):
    raw_text = message.caption or message.text or ""
    
    buttons_found = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    buttons_found.append((btn.text, btn.url))

    if not raw_text and not buttons_found:
        return None

    first_line = raw_text.split('\n')[0].strip() if raw_text else ""
    custom_link = buttons_found[0][1] if buttons_found else None

    urls = re.findall(r'https?://[^\s]+', first_line or raw_text)
    if not custom_link and urls:
        custom_link = urls[0]

    if not custom_link:
        custom_link = message.link

    parts = [p.strip() for p in first_line.split('|')] if first_line else []

    if len(parts) >= 3:
        story_name = parts[0]
        button_text = parts[1]
        link = parts[2]
        if not link.startswith("http"):
            link = custom_link

    elif len(parts) == 2:
        story_name = parts[0]
        button_text = parts[1]
        link = custom_link

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
    success = await db.save_post(caption_text=caption_format)
    
    if success:
        # दोनों मेथड्स (Request + Subscribe) को ट्रिगर करें
        asyncio.create_task(trigger_all_notifications(client, story_name))


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
        # दोनों मेथड्स (Request + Subscribe) को ट्रिगर करें
        asyncio.create_task(trigger_all_notifications(client, story_name))

        await message.reply_text(
            f"✅ **इंडेक्स हो गया!**\n\n"
            f"📖 **Story Name:** `{story_name}`\n"
            f"🔘 **Button Text:** `{button_text}`\n"
            f"🔗 **Link:** `{link}`"
        )
    else:
        await message.reply_text("⚠️ यह बटन या लिंक पहले से इस स्टोरी में मौजूद है।")


# 3. INDEX LAST POST COMMAND (/index_last)
@Client.on_message(filters.command("index_last") & filters.user(Config.OWNER_ID))
async def index_last_post_command(client, message):
    try:
        temp_msg = await client.send_message(Config.INDEX_CHANNEL, ".")
        last_id = temp_msg.id
        await temp_msg.delete()

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
        success = await db.save_post(caption_text=caption_format)
        
        if success:
            # दोनों मेथड्स (Request + Subscribe) को ट्रिगर करें
            asyncio.create_task(trigger_all_notifications(client, story_name))

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
