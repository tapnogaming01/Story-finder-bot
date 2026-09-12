import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from database import db
from rapidfuzz import process, fuzz
from plugins.start import check_verification
from config import Config

async def auto_delete_message(message, delay_seconds):
    """संदेश को निर्दिष्ट समय के बाद हटाने के लिए हेल्प फ़ंक्शन (FloodWait Safe)"""
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except FloodWait as e:
        await asyncio.sleep(e.value)
        try:
            await message.delete()
        except Exception:
            pass
    except Exception:
        pass

def extract_searched_number(text):
    """क्वेरी में से एपिसोड नंबर (जैसे 8, 9, 15) निकालता है"""
    numbers = re.findall(r'\b\d+\b', text)
    return int(numbers[-1]) if numbers else None

def is_number_in_button_text(searched_num, button_text):
    """चेक करता है कि सर्च किया गया नंबर बटन के Range या Episodic Text में आता है या नहीं"""
    if searched_num is None:
        return False
    
    # Range check (e.g., 1 to 10, 1-10, ep 1 to 10)
    range_match = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)', button_text, re.IGNORECASE)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        return start <= searched_num <= end
        
    # Single Episode check (e.g., ep 8, episode 8)
    single_nums = re.findall(r'\b\d+\b', button_text)
    if single_nums:
        return searched_num in [int(n) for n in single_nums]

    return False

def build_story_buttons_markup(buttons_list, page=0, story_id=""):
    """बटन्स की इनलाइन लिस्ट तैयार करता है"""
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_page_items = buttons_list[start:end]

    keyboard = []
    for item in current_page_items:
        btn_text = item.get("button_text", "Open Link")
        btn_url = item.get("link", "")
        keyboard.append([InlineKeyboardButton(text=btn_text, url=btn_url)])

    total_pages = (len(buttons_list) + page_size - 1) // page_size
    nav_buttons = []

    if page == 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data="last_page_alert"))
    else:
        nav_buttons.append(InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data=f"story_pg#{page - 1}#{story_id}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="pages_info"))

    if end < len(buttons_list):
        nav_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"story_pg#{page + 1}#{story_id}"))

    if total_pages > 1:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)


async def smart_search_handler(user_query):
    clean_query = user_query.strip()
    searched_num = extract_searched_number(clean_query)
    
    # नंबर हटाकर प्योर स्टोरी का नाम निकालें
    story_clean_query = re.sub(r'\b(?:ep|episode|e)?\s*\d+\b', '', clean_query, flags=re.IGNORECASE).strip()
    if not story_clean_query:
        story_clean_query = clean_query

    all_docs = await db.posts.find({}).to_list(length=None)
    if not all_docs:
        return None, [], "none"

    matched_buttons = []

    # 1. Exact Match Check
    for doc in all_docs:
        story_name = doc.get("story_name", "")
        
        # Exact Name Match (Case-Insensitive)
        if story_clean_query.lower() == story_name.lower() or story_clean_query.lower() in story_name.lower():
            
            # (A) अगर यूजर ने एपिसोड नंबर भी लिखा है
            if searched_num is not None:
                for btn in doc.get("buttons", []):
                    if is_number_in_button_text(searched_num, btn["button_text"]):
                        matched_buttons.append(btn)
                
                if matched_buttons:
                    return doc, matched_buttons, "direct_button"

            # (B) अगर यूजर ने सिर्फ सही स्टोरी नाम लिखा है
            return doc, doc.get("buttons", []), "story_all"

    # 2. Did You Mean Check
    all_story_names = [d.get("story_name") for d in all_docs if d.get("story_name")]
    best_matches = process.extract(
        story_clean_query,
        list(set(all_story_names)),
        scorer=fuzz.WRatio,
        limit=5
    )
    
    suggestions = [match[0] for match in best_matches if 55 <= match[1] < 100]
    return None, suggestions, "suggestion"


@Client.on_message(filters.text & (filters.private | filters.group) & ~filters.command(["start", "help", "about", "index", "index_last"]))
async def search_handler(client, message):
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return

    # Strict Force Sub Check (केवल PM के लिए)
    if message.chat.type.name == "PRIVATE":
        is_joined = await check_verification(client, user_id)
        if not is_joined:
            req_channel = str(Config.REQ_CHANNEL).replace("-100", "")
            invite_link = f"https://t.me/{Config.REQ_CHANNEL}" if not req_channel.isdigit() else f"https://t.me/c/{req_channel}/1"
            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=invite_link)],
                [InlineKeyboardButton("🔄 ᴠᴇʀɪғʏ / ᴛʀʏ ᴀɢᴀɪɴ", url=f"https://t.me/{client.me.username}?start=start")]
            ])
            await message.reply_text(
                "⚠️ **ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ!**\n\n"
                "ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ sᴇᴀʀᴄʜ sᴛᴏʀɪᴇs.",
                reply_markup=btn
            )
            return

    user_query = message.text.strip()

    # --- Step 1: Loading Message (Please Wait + User Query) ---
    loading_msg = await message.reply_text(f"⏳ <b>ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ</b>, {user_query}...**")
    await asyncio.sleep(1.5)

    story_doc, results, result_type = await smart_search_handler(user_query)

    # --- Step 2: अगर सजेशन पर जा रहा है ---
    if result_type == "suggestion":
        await loading_msg.edit_text("🤖 <b>ᴀɪ ᴄʜᴇᴄᴋɪɴɢ</b>")
        await asyncio.sleep(1.5)

    # --- Step 3: Direct Button या Exact Match ---
    if result_type in ["direct_button", "story_all"] and results:
        markup = build_story_buttons_markup(buttons_list=results, page=0, story_id=story_doc["story_name"])
        title_header = f"📖 **sᴛᴏʀʏ:** `{story_doc['story_name']}`"
        if result_type == "direct_button":
            title_header += f"\n🎯 **ᴍᴀᴛᴄʜᴇᴅ ᴇᴘɪsᴏᴅᴇ ʀᴇsᴜʟᴛ ғᴏʀ:** `{user_query}`"

        await loading_msg.edit_text(
            f"{title_header}\n"
            f"🔗 **ʙᴜᴛᴛᴏɴs ғᴏᴜɴᴅ:** `{len(results)}`\n\n"
            f"⏱️ _ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ 5 ᴍɪɴᴜᴛᴇs._",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(loading_msg, 300))
        return

    # --- Step 4: AI Suggestions / Did You Mean ---
    if result_type == "suggestion" and results:
        sug_buttons = []
        for sug in results:
            sug_buttons.append([InlineKeyboardButton(f"📖 {sug}", callback_data=f"dym_story#{sug}")])

        await loading_msg.edit_text(
            f"❌ **ɴᴏ ᴅɪʀᴇᴄᴛ ᴍᴀᴛᴄʜ ғᴏᴜɴᴅ ғᴏʀ `{user_query}`.**\n\n"
            f"**🤖 ᴅɪᴅ ʏᴏᴜ ᴍᴇᴀɴ?**\n\n"
            f"⏱️ _ᴛʜɪs sᴜɢɢᴇsᴛɪᴏɴ ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ 1 ᴍɪɴᴜᴛᴇ._",
            reply_markup=InlineKeyboardMarkup(sug_buttons)
        )
        asyncio.create_task(auto_delete_message(loading_msg, 60))
        return

    # --- Step 5: Silent Mode (अगर DB में डेटा न हो तो डिलीट) ---
    try:
        await loading_msg.delete()
    except Exception:
        pass


@Client.on_callback_query(filters.regex(r"^dym_story#"))
async def dym_story_callback(client, query):
    user_id = query.from_user.id

    if not await check_verification(client, user_id):
        await query.answer("ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ!", show_alert=True)
        return

    story_name = query.data.split("#")[1]
    story_doc = await db.posts.find_one({"story_name": story_name})

    if story_doc and story_doc.get("buttons"):
        try:
            await query.message.delete()
        except Exception:
            pass

        markup = build_story_buttons_markup(buttons_list=story_doc["buttons"], page=0, story_id=story_name)
        total_btns = len(story_doc["buttons"])
        
        sent_msg = await client.send_message(
            chat_id=query.message.chat.id,
            text=(
                f"📖 **sᴛᴏʀʏ:** `{story_doc['story_name']}`\n"
                f"🔗 **ᴀᴠᴀɪʟᴀʙʟᴇ ʟɪɴᴋs/ᴇᴘɪsᴏᴅᴇs:** `{total_btns}`\n\n"
                f"⏱️ _ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ 5 ᴍɪɴᴜᴛᴇs._"
            ),
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(sent_msg, 300))
        await query.answer()
    else:
        await query.answer("ɴᴏ ʙᴜᴛᴛᴏɴs ғᴏᴜɴᴅ ғᴏʀ ᴛʜɪs sᴛᴏʀʏ!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^story_pg#"))
async def story_pagination_callback(client, query):
    if not await check_verification(client, query.from_user.id):
        await query.answer("ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ғɪʀsᴛ!", show_alert=True)
        return

    _, page_str, story_name = query.data.split("#")
    page = int(page_str)

    story_doc = await db.posts.find_one({"story_name": story_name})
    if not story_doc or not story_doc.get("buttons"):
        await query.answer("sᴛᴏʀʏ ᴅᴀᴛᴀ ᴇxᴘɪʀᴇᴅ!", show_alert=True)
        return

    markup = build_story_buttons_markup(buttons_list=story_doc["buttons"], page=page, story_id=story_name)
    total_btns = len(story_doc["buttons"])
    
    await query.message.edit_text(
        f"📖 **sᴛᴏʀʏ:** `{story_doc['story_name']}`\n"
        f"🔗 **ᴀᴠᴀɪʟᴀʙʟᴇ ʟɪɴᴋs/ᴇᴘɪsᴏᴅᴇs:** `{total_btns}`\n\n"
        f"⏱️ _ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ɪɴ 5 ᴍɪɴᴜᴛᴇs._",
        reply_markup=markup
    )


@Client.on_callback_query(filters.regex("^last_page_alert$"))
async def last_page_alert_callback(client, query):
    await query.answer("ᴛʜɪs ɪs ᴛʜᴇ ғɪʀsᴛ/ʟᴀsᴛ ᴘᴀɢᴇ", show_alert=True)


@Client.on_callback_query(filters.regex("^pages_info$"))
async def pages_info_callback(client, query):
    await query.answer("ᴄᴜʀʀᴇɴᴛ ᴘᴀɢᴇ ɴᴜᴍʙᴇʀ", show_alert=False)
