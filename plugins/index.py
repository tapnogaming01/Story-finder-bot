import re
from pyrogram import Client, filters
from config import Config
from database import db

def extract_episode(text):
    match = re.search(r'(?:ep|episode|e)\s*(\d+)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'\b(\d{1,3})\b', text)
    return int(match.group(1)) if match else None

def parse_post_content(message):
    raw_text = message.caption or message.text or ""
    if not raw_text:
        return None, None, None

    custom_link = None
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for btn in row:
                if btn.url:
                    custom_link = btn.url
                    break

    urls = re.findall(r'https?://[^\s]+', raw_text)
    if not custom_link and urls:
        custom_link = urls[0]

    if not custom_link:
        custom_link = message.link

    first_line = raw_text.split('\n')[0].strip()
    if "|" in first_line:
        title = first_line.split("|")[0].strip()
    else:
        title = re.sub(r'https?://[^\s]+', '', first_line).strip()

    episode = extract_episode(first_line)
    return title, custom_link, episode

@Client.on_message(filters.channel & filters.chat(Config.INDEX_CHANNEL))
async def auto_index_handler(client, message):
    title, link, episode = parse_post_content(message)
    if not title or not link:
        return

    await db.save_post(title=title, link=link, episode=episode)
