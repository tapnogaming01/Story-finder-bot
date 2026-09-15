import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from config import Config

async def get_settings_markup():
    current_style = await db.get_bot_style()
    
    btn_tick = "✅ " if current_style == "button" else ""
    text_tick = "✅ " if current_style == "text" else ""

    buttons = [
        [
            InlineKeyboardButton(f"{btn_tick}🔘 Button Format", callback_data="set_style#button"),
            InlineKeyboardButton(f"{text_tick}📝 Text Format", callback_data="set_style#text")
        ],
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
        "⚙️ **Admin Settings: Search Result Format**\n\n"
        "आप अपने यूज़र्स को सर्च रिजल्ट किस फ़ॉर्मेट में दिखाना चाहते हैं? नीचे से चुनें:",
        reply_markup=markup
    )

# 🔄 Toggle Callback (Green Tick Changer)
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
        "⚙️ **Admin Settings: Search Result Format**\n\n"
        "बॉट का फ़ॉर्मेट सफलतापूर्वक बदल दिया गया है! ✅",
        reply_markup=markup
    )
    await query.answer("Format Updated Globally!")

@Client.on_callback_query(filters.regex("^close_settings$"))
async def close_settings_callback(client, query):
    await query.message.delete()
