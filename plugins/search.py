import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from rapidfuzz import process, fuzz
from plugins.start import check_verification

async def auto_delete_message(message, delay_seconds):
    """संदेश को निर्दिष्ट समय के बाद हटाने के लिए हेल्प फ़ंक्शन"""
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except Exception:
        pass

def build_story_buttons_markup(story_doc, page=0, story_id=""):
    """किसी विशिष्ट स्टोरी के अंदर के बटन्स (Button Text + Link) के लिए पेजिंग तैयार करता है"""
    buttons_list = story_doc.get("buttons", [])
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_page_items = buttons_list[start:end]

    keyboard = []
    # स्टोरी के अंदर सेव किए गए बटन्स बनाएं
    for item in current_page_items:
        btn_text = item.get("button_text", "Open Link")
        btn_url = item.get("link", "")
        keyboard.append([InlineKeyboardButton(text=btn_text, url=btn_url)])

    total_pages = (len(buttons_list) + page_size - 1) // page_size
    nav_buttons = []

    if page == 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data="last_page_alert"))
    else:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"story_pg#{page - 1}#{story_id}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="pages_info"))

    if end < len(buttons_list):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"story_pg#{page + 1}#{story_id}"))

    if total_pages > 1:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)


async def search_stories_logic(user_query):
    """सर्च क्वेरी को प्रोसेस करके Story document या Suggestions रिटर्न करता है"""
    clean_query = user_query.strip()
    if not clean_query:
        return None, []

    # 1. Direct Regex Search on Story Names
    matched_stories = await db.get_story_suggestions(clean_query)
    
    if matched_stories:
        # अगर direct match मिला तो पहला matched story return करें
        return matched_stories[0], []

    # 2. Fuzzy Matching for "Did You Mean" Suggestions
    all_story_names = await db.get_all_story_names()
    if not all_story_names:
        return None, []

    best_matches = process.extract(
        clean_query,
        all_story_names,
        scorer=fuzz.WRatio,
        limit=5
    )
    
    # 55% से अधिक मैच होने पर स्टोरी के नामों के सजेशन्स तैयार करें
    suggestions = [match[0] for match in best_matches if match[1] >= 55]
    return None, suggestions


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
    matched_story, suggestions = await search_stories_logic(user_query)

    # 1. MATCH FOUND -> स्टोरी के बटन्स दिखाएं (5 Min Auto Delete)
    if matched_story:
        markup = build_story_buttons_markup(story_doc=matched_story, page=0, story_id=matched_story["story_name"])
        total_btns = len(matched_story.get("buttons", []))
        sent_msg = await message.reply_text(
            f"📖 **Story:** `{matched_story['story_name']}`\n"
            f"🔗 **Available Links/Episodes:** `{total_btns}`\n\n"
            f"⏱️ _This message will be deleted in 5 minutes._",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(sent_msg, 300))
        return

    # 2. DID YOU MEAN SUGGESTIONS -> केवल Story Names के बटन्स (1 Min Auto Delete)
    if suggestions:
        sug_buttons = []
        for sug in suggestions:
            # बटन में केवल Story Name दिखेगा
            sug_buttons.append([InlineKeyboardButton(f"📖 {sug}", callback_data=f"dym_story#{sug}")])

        sent_msg = await message.reply_text(
            f"❌ No match found for `{user_query}`.\n\n**Did you mean?**\n\n"
            f"⏱️ _This suggestion message will be deleted in 1 minute._",
            reply_markup=InlineKeyboardMarkup(sug_buttons)
        )
        asyncio.create_task(auto_delete_message(sent_msg, 60))
        return

    # 3. SILENT MODE: डेटाबेस से बाहर होने पर बोट पूरी तरह शांत रहेगा।


@Client.on_callback_query(filters.regex(r"^dym_story#"))
async def dym_story_callback(client, query):
    """यूजर जब 'Did You Mean' के Story Name बटन पर क्लिक करेगा"""
    if not await check_verification(client, query.from_user.id):
        await query.answer("Please join our update channel first!", show_alert=True)
        return

    story_name = query.data.split("#")[1]
    story_doc = await db.get_story_by_name(story_name)

    if story_doc:
        markup = build_story_buttons_markup(story_doc=story_doc, page=0, story_id=story_name)
        total_btns = len(story_doc.get("buttons", []))
        await query.message.edit_text(
            f"📖 **Story:** `{story_doc['story_name']}`\n"
            f"🔗 **Available Links/Episodes:** `{total_btns}`\n\n"
            f"⏱️ _This message will be deleted in 5 minutes._",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(query.message, 300))
    else:
        await query.answer("No buttons found for this story!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^story_pg#"))
async def story_pagination_callback(client, query):
    """स्टोरी के अंदर के बटन्स के लिए Pagination Callback (Next/Back)"""
    if not await check_verification(client, query.from_user.id):
        await query.answer("Please join our update channel first!", show_alert=True)
        return

    _, page_str, story_name = query.data.split("#")
    page = int(page_str)

    story_doc = await db.get_story_by_name(story_name)
    if not story_doc:
        await query.answer("Story data expired!", show_alert=True)
        return

    markup = build_story_buttons_markup(story_doc=story_doc, page=page, story_id=story_name)
    total_btns = len(story_doc.get("buttons", []))
    await query.message.edit_text(
        f"📖 **Story:** `{story_doc['story_name']}`\n"
        f"🔗 **Available Links/Episodes:** `{total_btns}`\n\n"
        f"⏱️ _This message will be deleted in 5 minutes._",
        reply_markup=markup
    )


@Client.on_callback_query(filters.regex("^last_page_alert$"))
async def last_page_alert_callback(client, query):
    await query.answer("This is the first/last page", show_alert=True)


@Client.on_callback_query(filters.regex("^pages_info$"))
async def pages_info_callback(client, query):
    await query.answer("Current Page Number", show_alert=False)
