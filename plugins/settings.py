import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import Config

async def get_settings_markup():
    current_style = await db.get_bot_style()
    # Database से current limit लाएं (default 5 अगर सेट न हो)
    current_limit = await db.get_page_limit()
    
    # Format Ticks
    btn_tick = "✅ " if current_style == "button" else ""
    text_tick = "✅ " if current_style == "text" else ""

    # Page Limit Ticks
    limit_5_tick = "✅ " if current_limit == 5 else ""
    limit_10_tick = "✅ " if current_limit == 10 else ""

    buttons = [
        # 📌 Row 1: Search Result Format
        [
            InlineKeyboardButton(f"{btn_tick}🔘 Button Format", callback_data="set_style#button"),
            InlineKeyboardButton(f"{text_tick}📝 Text Format", callback_data="set_style#text")
        ],
        # 📌 Row 2: Page Limit Settings (5 or 10 Results)
        [
            InlineKeyboardButton(f"{limit_5_tick}📄 5 Results/Page", callback_data="set_limit#5"),
            InlineKeyboardButton(f"{limit_10_tick}📄 10 Results/Page", callback_data="set_limit#10")
        ],
        # 📌 Row 3: Close Button
        [InlineKeyboardButton("❌ Close", callback_data="close_settings")]
    ]
    return InlineKeyboardMarkup(buttons)

# 🛠️ /settings Command (OWNER ONLY)
@Client.on_message(filters.command(["settings", "mode"]) & filters.private)
async def settings_handler(client, message):
    user_id = message.from_user.id
    
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        await message.reply_text("❌ **Access Denied!** यह कमांड सिर्फ़ बॉट ऑनर के लिए है।")
        return

    markup = await get_settings_markup()
    await message.reply_text(
        "⚙️ **Admin Control Panel**\n\n"
        "यहाँ से आप **Search Format** और **Per Page Results Limit** सेट कर सकते हैं:",
        reply_markup=markup
    )

# 🔄 Style Toggle Callback (Format Changer)
@Client.on_callback_query(filters.regex(r"^set_style#"))
async def style_toggle_callback(client, query):
    user_id = query.from_user.id
    
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        await query.answer("❌ सिर्फ़ ऑनर ही फ़ॉर्मेट बदल सकता है!", show_alert=True)
        return

    new_style = query.data.split("#")[1]
    current_style = await db.get_bot_style()
    
    if current_style == new_style:
        await query.answer("यह फ़ॉर्मेट पहले से सेलेक्टेड है!", show_alert=False)
        return

    await db.set_bot_style(new_style)
    markup = await get_settings_markup()
    
    await query.message.edit_text(
        "⚙️ **Admin Control Panel**\n\n"
        "बॉट का सर्च फ़ॉर्मेट सफलतापूर्वक बदल दिया गया है! ✅",
        reply_markup=markup
    )
    await query.answer("Format Updated Globally!")

# 🔢 Page Limit Callback (5 या 10 Limits Changer)
@Client.on_callback_query(filters.regex(r"^set_limit#"))
async def limit_toggle_callback(client, query):
    user_id = query.from_user.id
    
    if user_id not in Config.ADMINS and user_id != Config.OWNER_ID:
        await query.answer("❌ सिर्फ़ ऑनर ही पेज लिमिट बदल सकता है!", show_alert=True)
        return

    new_limit = int(query.data.split("#")[1])
    current_limit = await db.get_page_limit()
    
    if current_limit == new_limit:
        await query.answer(f"पेज लिमिट पहले से ही {new_limit} पर सेलेक्टेड है!", show_alert=False)
        return

    # Database में new limit को सेभ करें
    await db.set_page_limit(new_limit)
    markup = await get_settings_markup()
    
    await query.message.edit_text(
        "⚙️ **Admin Control Panel**\n\n"
        f"पेज रिजल्ट्स लिमिट सफलतापूर्वक **{new_limit} Results/Page** सेट कर दी गई है! ✅",
        reply_markup=markup
    )
    await query.answer(f"Page Limit Updated to {new_limit}!")

@Client.on_callback_query(filters.regex("^close_settings$"))
async def close_settings_callback(client, query):
    await query.message.delete()
