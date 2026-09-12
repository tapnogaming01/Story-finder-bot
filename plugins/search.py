import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import Config
from rapidfuzz import process, fuzz
from plugins.start import check_verification

async def auto_delete_message(message, delay_seconds):
    """संदेश को ऑटो-डिलीट करने का फ़ंक्शन"""
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except Exception:
        pass

def extract_searched_episode(text):
    """सर्च क्वेरी में से नंबर निकालता है (उदा: 9 या episode 9)"""
    match = re.search(r'\b(\d+)\b', text)
    return int(match.group(1)) if match else None

def is_num_in_range(num, text):
    """चेक करता है कि नंबर बटन के नाम (जैसे '1 To 10' या '1-10') में आता है या नहीं"""
    if not num or not text:
        return False
    # Check single number match
    if str(num) == str(text).strip():
        return True
    # Range check like 1-10, 1 to 10
    ranges = re.findall(r'(\d+)\s*(?:to|-)\s*(\d+)', str(text), re.IGNORECASE)
    for start, end in ranges:
        if int(start) <= num <= int(end):
            return True
    return False

def build_pagination_markup(results, page=0, query_text=""):
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_page_items = results[start:end]

    buttons = []
    for item in current_page_items:
        # बटन का नाम या तो custom name होगा या fallback Title
        btn_label = item.get("button_name") or item.get("title")
        buttons.append([InlineKeyboardButton(btn_label, url=item["link"])])

    total_pages = (len(results) + page_size - 1) // page_size
    nav_buttons = []

    if page == 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="last_page_alert"))
    else:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"search_pg#{page - 1}#{query_text}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="pages_info"))

    if end < len(results):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_pg#{page + 1}#{query_text}"))

    if total_pages > 1:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(buttons)

async def get_search_results(user_query):
    all_docs = await db.get_all_posts()
    if not all_docs:
        return [], None

    query_clean = user_query.strip().lower()
    searched_num = extract_searched_episode(user_query)

    matched_items = []
    story_titles_set = set()

    for doc in all_docs:
        story_title = doc.get("title", "")
        story_titles_set.add(story_title)

        links_list = doc.get("links", [])
        for link_obj in links_list:
            btn_name = link_obj.get("button_name") or link_obj.get("episode_info") or "Open Link"
            link = link_obj.get("link", "")
            btn_name_str = str(btn_name).lower()

            # 1. Story Title या Button Name पाठ्य से मैच होना
            is_direct_match = (query_clean in story_title.lower()) or (query_clean in btn_name_str)

            # 2. Episode/Number Range match (जैसे '9' लिखने पर 1 To 10 वाला बटन मिलना)
            is_number_match = False
            if searched_num and is_num_in_range(searched_num, btn_name_str):
                is_number_match = True

            if is_direct_match or is_number_match:
                matched_items.append({
                    "title": story_title,
                    "button_name": btn_name,
                    "link": link
                })

    # अगर डायरेक्ट या नंबर मैच मिल गया
    if matched_items:
        return matched_items, None

    # अगर exact match नहीं मिला तो Did You Mean के लिए सिर्फ Unique Story Titles यूज़ होंगे
    best_matches = process.extract(
        user_query,
        list(story_titles_set),
        scorer=fuzz.WRatio,
        limit=5
    )
    suggestions = [match[0] for match in best_matches if match[1] >= 50]
    return [], list(set(suggestions))


@Client.on_message(filters.text & filters.private & ~filters.command(["start", "help", "about", "index", "index_last"]))
async def search_handler(client, message):
    user_id = message.from_user.id

    # 🛑 Strict Force Sub Verification Check
    is_joined = await check_verification(client, user_id)
    if not is_joined:
        req_channel = str(Config.REQ_CHANNEL).replace("-100", "")
        invite_link = f"https://t.me/{Config.REQ_CHANNEL}" if not req_channel.isdigit() else f"https://t.me/c/{req_channel}/1"
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Update Channel", url=invite_link)],
            [InlineKeyboardButton("🔄 Verify / Try Again", url=f"https://t.me/{client.me.username}?start=start")]
        ])
        await message.reply_text(
            "⚠️ **Access Denied!**\n\n"
            "ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ sᴇᴀʀᴄʜ sᴛᴏʀɪᴇs.",
            reply_markup=btn
        )
        return

    user_query = message.text
    matched_items, suggestions = await get_search_results(user_query)

    # 1. MATCH FOUND -> (स्टोरी के बटन उनके लिंक के साथ शो होंगे)
    if matched_items:
        markup = build_pagination_markup(results=matched_items, page=0, query_text=user_query)
        sent_msg = await message.reply_text(
            f"🔍 **Search Results for:** `{user_query}`\nTotal Buttons: `{len(matched_items)}`\n\n"
            f"⏱️ _This message will be deleted in 5 minutes._",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(sent_msg, 300))
        return

    # 2. DID YOU MEAN SUGGESTION -> (केवल स्टोरी नेम के बटन शो होंगे)
    if suggestions:
        sug_buttons = []
        for sug_title in suggestions:
            sug_buttons.append([InlineKeyboardButton(f"🔍 {sug_title}", callback_data=f"dym_search#{sug_title}")])

        sent_msg = await message.reply_text(
            f"❌ No exact match for `{user_query}`.\n\n**Did you mean?**\n\n"
            f"⏱️ _This suggestion message will be deleted in 1 minute._",
            reply_markup=InlineKeyboardMarkup(sug_buttons)
        )
        asyncio.create_task(auto_delete_message(sent_msg, 60))
        return

    # 3. SILENT MODE: डेटाबेस से मैच न होने पर बॉट बिल्कुल शांत रहेगा।


@Client.on_callback_query(filters.regex(r"^dym_search#"))
async def dym_callback(client, query):
    if not await check_verification(client, query.from_user.id):
        await query.answer("Please join our update channel first!", show_alert=True)
        return

    sug_story_title = query.data.split("#")[1]
    matched_items, _ = await get_search_results(sug_story_title)

    if matched_items:
        markup = build_pagination_markup(results=matched_items, page=0, query_text=sug_story_title)
        await query.message.edit_text(
            f"📖 **Story:** `{sug_story_title}`\nTotal Buttons: `{len(matched_items)}`\n\n"
            f"⏱️ _This message will be deleted in 5 minutes._",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(query.message, 300))
    else:
        await query.answer("No buttons found for this story!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^search_pg#"))
async def pagination_callback(client, query):
    if not await check_verification(client, query.from_user.id):
        await query.answer("Please join our update channel first!", show_alert=True)
        return

    _, page_str, query_text = query.data.split("#")
    page = int(page_str)

    matched_items, _ = await get_search_results(query_text)
    if not matched_items:
        await query.answer("Results expired!", show_alert=True)
        return

    markup = build_pagination_markup(results=matched_items, page=page, query_text=query_text)
    await query.message.edit_text(
        f"🔍 **Search Results for:** `{query_text}`\nTotal Buttons: `{len(matched_items)}`\n\n"
        f"⏱️ _This message will be deleted in 5 minutes._",
        reply_markup=markup
    )


@Client.on_callback_query(filters.regex("^last_page_alert$"))
async def last_page_alert_callback(client, query):
    await query.answer("This is the last page", show_alert=True)


@Client.on_callback_query(filters.regex("^pages_info$"))
async def pages_info_callback(client, query):
    await query.answer("Current Page Number", show_alert=False)
