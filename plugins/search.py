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

def extract_searched_episode(text):
    """सर्च क्वेरी में से एपिसोड नंबर निकालता है"""
    match = re.search(r'(?:ep|episode|e)?\s*(\d+)$', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def check_episode_in_range(user_ep, ep_info):
    """चेक करता है कि यूजर का एपिसोड रेंज (1-10) या सिंगल नंबर में फिट होता है या नहीं"""
    if not ep_info or not user_ep:
        return True
    
    if "-" in str(ep_info):
        try:
            start, end = map(int, str(ep_info).split("-"))
            return start <= int(user_ep) <= end
        except ValueError:
            return False
            
    return str(user_ep) == str(ep_info)

def build_pagination_markup(results, page=0, query_text=""):
    page_size = 10
    start = page * page_size
    end = start + page_size
    current_page_items = results[start:end]

    buttons = []
    for item in current_page_items:
        p_ep = item.get("episode_info")
        btn_label = f"{item['title']}" + (f" [EP {p_ep}]" if p_ep else "")
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
    searched_ep = extract_searched_episode(user_query)
    
    clean_title = re.sub(r'(?:ep|episode|e)?\s*\d+(?:\s*(?:-|to)\s*\d+)?', '', user_query, flags=re.IGNORECASE).strip()
    if not clean_title:
        clean_title = user_query.strip()

    all_docs = await db.get_all_posts()
    if not all_docs:
        return [], None

    matched_items = []
    all_titles = []

    for doc in all_docs:
        title = doc.get("title", "")
        all_titles.append(title)

        if clean_title.lower() in title.lower():
            for link_obj in doc.get("links", []):
                ep_info = link_obj.get("episode_info")
                
                if searched_ep and ep_info:
                    if check_episode_in_range(searched_ep, ep_info):
                        matched_items.append({
                            "title": title,
                            "link": link_obj["link"],
                            "episode_info": ep_info
                        })
                else:
                    matched_items.append({
                        "title": title,
                        "link": link_obj["link"],
                        "episode_info": ep_info
                    })

    if matched_items:
        return matched_items, None

    best_matches = process.extract(
        clean_title,
        list(set(all_titles)),
        scorer=fuzz.WRatio,
        limit=5
    )
    suggestions = [match[0] for match in best_matches if match[1] >= 55]
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
        return  # 👈 Is line se aage ka search logic run nahi hoga jab tak user join nahi karega

    user_query = message.text
    matched_items, suggestions = await get_search_results(user_query)

    # 1. MATCH FOUND -> 5 Minutes Auto Delete
    if matched_items:
        markup = build_pagination_markup(results=matched_items, page=0, query_text=user_query)
        sent_msg = await message.reply_text(
            f"🔍 **Search Results for:** `{user_query}`\nTotal: `{len(matched_items)}` items\n\n"
            f"⏱️ _This message will be deleted in 5 minutes._",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(sent_msg, 300))
        return

    # 2. DID YOU MEAN SUGGESTION -> 1 Minute Auto Delete
    if suggestions:
        sug_buttons = []
        for sug in suggestions:
            sug_buttons.append([InlineKeyboardButton(f"🔍 {sug}", callback_data=f"dym_search#{sug}")])

        sent_msg = await message.reply_text(
            f"❌ No match found for `{user_query}`.\n\n**Did you mean?**\n\n"
            f"⏱️ _This suggestion message will be deleted in 1 minute._",
            reply_markup=InlineKeyboardMarkup(sug_buttons)
        )
        asyncio.create_task(auto_delete_message(sent_msg, 60))
        return

    # 3. SILENT MODE: Out off database matching will stay completely silent.


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
        f"🔍 **Search Results for:** `{query_text}`\nTotal: `{len(matched_items)}` items\n\n"
        f"⏱️ _This message will be deleted in 5 minutes._",
        reply_markup=markup
    )


@Client.on_callback_query(filters.regex(r"^dym_search#"))
async def dym_callback(client, query):
    if not await check_verification(client, query.from_user.id):
        await query.answer("Please join our update channel first!", show_alert=True)
        return

    sug_title = query.data.split("#")[1]
    matched_items, _ = await get_search_results(sug_title)

    if matched_items:
        markup = build_pagination_markup(results=matched_items, page=0, query_text=sug_title)
        await query.message.edit_text(
            f"🔍 **Search Results for:** `{sug_title}`\nTotal: `{len(matched_items)}` items\n\n"
            f"⏱️ _This message will be deleted in 5 minutes._",
            reply_markup=markup
        )
        asyncio.create_task(auto_delete_message(query.message, 300))
    else:
        await query.answer("No data found!", show_alert=True)


@Client.on_callback_query(filters.regex("^last_page_alert$"))
async def last_page_alert_callback(client, query):
    await query.answer("This is the last page", show_alert=True)


@Client.on_callback_query(filters.regex("^pages_info$"))
async def pages_info_callback(client, query):
    await query.answer("Current Page Number", show_alert=False)


