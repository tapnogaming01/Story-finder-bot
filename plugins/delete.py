from pyrogram import Client, filters
from config import Config
from database import db

# 1. पूरी एक स्टोरी डिलीट करने का कमांड (/delete Story Name)
@Client.on_message(filters.command("delete") & filters.user(Config.OWNER_ID))
async def delete_single_story_command(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "⚠️ **उपयोग कैसे करें:**\n\n"
            "`/delete <Story Name>`\n\n"
            "**उदाहरण:** `/delete My possessive saiyaan`"
        )
        return

    story_name = message.text.split(maxsplit=1)[1].strip()
    
    # DB से डिलीट करें
    deleted = await db.delete_story(story_name)

    if deleted:
        await message.reply_text(f"✅ स्टोरी **'{story_name}'** और उसके सभी बटन्स डेटाबेस से डिलीट कर दिए गए हैं!")
    else:
        await message.reply_text(f"❌ **'{story_name}'** नाम की कोई स्टोरी डेटाबेस में नहीं मिली।")


# 2. स्टोरी के अंदर से सिर्फ एक बटन डिलीट करने का कमांड (/del_btn Story | Button)
@Client.on_message(filters.command("del_btn") & filters.user(Config.OWNER_ID))
async def delete_button_command(client, message):
    if len(message.command) < 2 or "|" not in message.text:
        await message.reply_text(
            "⚠️ **उपयोग कैसे करें:**\n\n"
            "`/del_btn Story Name | Button Text`\n\n"
            "**उदाहरण:** `/del_btn My possessive saiyaan | Ep 1 To 10`"
        )
        return

    raw_args = message.text.split(maxsplit=1)[1]
    parts = [p.strip() for p in raw_args.split("|")]

    if len(parts) < 2:
        await message.reply_text("❌ कृपया सही फॉर्मेट का पालन करें: `Story Name | Button Text`")
        return

    story_name = parts[0]
    button_text = parts[1]

    removed = await db.delete_button_from_story(story_name, button_text)

    if removed:
        await message.reply_text(f"✅ स्टोरी **'{story_name}'** से बटन **'{button_text}'** डिलीट कर दिया गया है!")
    else:
        await message.reply_text("❌ मैचिंग स्टोरी या बटन नहीं मिला।")


# 3. पूरा डेटाबेस खाली करने का कमांड (/drop_all)
@Client.on_message(filters.command("drop_all") & filters.user(Config.OWNER_ID))
async def drop_all_database_command(client, message):
    # सुरक्षा के लिए कन्फर्मेशन मैसेज
    if len(message.command) == 1:
        await message.reply_text(
            "🚨 **चेतावनी!** क्या आप सच में पूरा डेटाबेस खाली (Delete All) करना चाहते हैं?\n\n"
            "पुष्टि करने के लिए लिखें: `/drop_all confirm`"
        )
        return

    if message.command[1].lower() == "confirm":
        await db.drop_all_posts()
        await message.reply_text("🗑️ **डेटाबेस पूरी तरह से खाली कर दिया गया है!** सभी इंडेक्स पोस्ट डिलीट हो चुकी हैं।")
    else:
        await message.reply_text("❌ गलत पुष्टि कोड। डिलीट प्रक्रिया रद्द कर दी गई है।")
