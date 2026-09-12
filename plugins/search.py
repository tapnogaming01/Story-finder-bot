import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from rapidfuzz import process, fuzz
from plugins.start import check_verification

async def auto_delete_message(message, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except Exception:
        pass

def build_pagination_markup(results, page=0, query_text=""):
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_page_items = results[start:end]

    buttons = []
    for post in current_page_items:
        p_ep = post.get("episode")
        btn_label = f"{post['display_title']}" + (f" [EP {p_ep}]" if p_ep else "")
        buttons.append([InlineKeyboardButton(btn_label, url=post["link"])])

    total_pages = (len(results) + page_size - 1) // page_size
    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"search_pg#{page - 1}#{query_text}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="pages_info"))

    if end < len(results):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_pg#{page + 1}#{query_text}"))

    if total_pages > 1:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(buttons)

def parse_query(query_text):
    ep_match = re.search(r'(?:ep|episode|e)?\s*(\d+)$', query_text, re.IGNORECASE)
    if ep_match:
        episode = int(ep_match.group(1))
        clean_title = query_text[:ep_match.start()].strip()
        return clean_title, episode
    return query_text.strip(), None

async def get_search_results(user_query):
    clean_title, req_ep = parse_query(user_query)
    all_posts = await db.get_all_posts()
    if not all_posts:
        return [], None, clean_title

    matched_posts = []
    titles_list = [p["display_title"] for p in all_posts]

    for post in all_posts:
        p_title = post["display_title"]
        p_ep = post.get("episode")

        if clean_title.lower() in p_title.lower():
            if req_ep is not None:
                if p_ep == req_ep:
                    matched_posts.append(post)
            else:
                matched_posts.append(post)

    if matched_posts:
        return matched_posts, None, clean_title

    best_matches = process.extract(
        clean_title,
        titles_list,
        scorer=fuzz.WRatio,
        limit=5
    )
    suggestions = [match[0] for match in best_matches if match[1] >= 55]
    return [], list(set(suggestions)), clean_title


@Client.on_message(filters.text & ~filters.command(["start", "help", "about"]))
async def search_handler(client, message):
    if not await check_verification(client, message.from_user.id):
        await message.reply_text("⚠️ **सर्च करने से पहले कृपया /start पर क्लिक करके चैनल जॉइन करें!**")
        return

    user_query = message.text
    matched_posts, suggestions, clean_title = await get_search_results(user_query)

    # Search Match Found -> 5 Min Auto Delete (300 sec)
    if matched_posts:
        markup = build_pagination_markup(results=matched_posts, page=0, query_text=user_query)
        sent_msg = await message.reply_text(
            f"🔍 **Search Results for:** `{user_query}`\nTotal: `{len(matched_posts)}` items\n\n"
            f"⏱️ _यह मैसेज 5 मिनट में डिलीट हो जाएगा।_",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(sent_msg, 300))
        return

    # Did You Mean Suggestion -> 1 Min Auto Delete (60 sec)
    if suggestions:
        sug_buttons = []
        for sug in suggestions:
            sug_buttons.append([InlineKeyboardButton(f"🔍 {sug}", callback_data=f"dym_search#{sug}")])

        sent_msg = await message.reply_text(
            f"❌ `{user_query}` का कोई मैच नहीं मिला।\n\n**क्या आपका मतलब यह था? (Did you mean?):**\n\n"
            f"⏱️ _यह सुझाव संदेश 1 मिनट में डिलीट हो जाएगा।_",
            reply_markup=InlineKeyboardMarkup(sug_buttons)
        )
        asyncio.create_task(auto_delete_message(sent_msg, 60))


@Client.on_callback_query(filters.regex(r"^search_pg#"))
async def pagination_callback(client, query):
    _, page_str, query_text = query.data.split("#")
    page = int(page_str)

    matched_posts, _, _ = await get_search_results(query_text)
    if not matched_posts:
        await query.answer("रिजल्ट्स एक्सपायर हो चुके हैं!", show_alert=True)
        return

    markup = build_pagination_markup(results=matched_posts, page=page, query_text=query_text)
    await query.message.edit_text(
        f"🔍 **Search Results for:** `{query_text}`\nTotal: `{len(matched_posts)}` items\n\n"
        f"⏱️ _यह मैसेज 5 मिनट में डिलीट हो जाएगा।_",
        reply_markup=markup
    )


@Client.on_callback_query(filters.regex(r"^dym_search#"))
async def dym_callback(client, query):
    sug_title = query.data.split("#")[1]
    matched_posts, _, _ = await get_search_results(sug_title)

    if matched_posts:
        markup = build_pagination_markup(results=matched_posts, page=0, query_text=sug_title)
        await query.message.edit_text(
            f"🔍 **Search Results for:** `{sug_title}`\nTotal: `{len(matched_posts)}` items\n\n"
            f"⏱️ _यह मैसेज 5 मिनट में डिलीट हो जाएगा।_",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(query.message, 300))
    else:
        await query.answer("कोई डेटा नहीं मिला!", show_alert=True)


@Client.on_callback_query(filters.regex("^pages_info$"))
async def pages_info_callback(client, query):
    await query.answer("यह वर्तमान पेज संख्या है।", show_alert=False)
