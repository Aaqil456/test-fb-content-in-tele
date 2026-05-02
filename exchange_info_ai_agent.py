import sys
import os
import asyncio
from telethon import TelegramClient
from utils.google_sheet_reader import fetch_channels_from_google_sheet
from utils.telegram_reader import extract_channel_username, fetch_latest_messages
from utils.ai_translator import translate_text_gemini
from utils.telegram_sender import send_telegram_message_html, send_media_group_to_telegram
from utils.json_writer import save_results, load_posted_messages

async def main():
    telegram_api_id = os.environ['TELEGRAM_API_ID']
    telegram_api_hash = os.environ['TELEGRAM_API_HASH']
    sheet_id = os.environ['GOOGLE_SHEET_ID']
    google_sheet_api_key = os.environ['GOOGLE_SHEET_API_KEY']

    posted_messages = load_posted_messages()
    result_output = []
    channels_data = fetch_channels_from_google_sheet(sheet_id, google_sheet_api_key)

    for entry in channels_data:
        channel_username = extract_channel_username(entry["channel_link"])
        sumber_info = entry.get("sumber", "") # Get source from sheet entry
        messages = await fetch_latest_messages(telegram_api_id, telegram_api_hash, channel_username)

        for msg in messages:
            if str(msg["id"]) in posted_messages or msg["text"] in posted_messages:
                continue

            translated = translate_text_gemini(msg["text"])
            photo_paths = []

            if msg.get("photos"):
                async with TelegramClient("telegram_session", telegram_api_id, telegram_api_hash) as client:
                    for i, photo_media in enumerate(msg["photos"]):
                        path = f"photo_{msg['id']}_{i}.jpg"
                        await client.download_media(photo_media, path)
                        photo_paths.append(path)

                send_media_group_to_telegram(
                    image_paths=photo_paths,
                    translated_caption=translated,
                    sumber=sumber_info # Pass source to sender
                )

                for p in photo_paths:
                    if os.path.exists(p): os.remove(p)
            else:
                send_telegram_message_html(
                    translated_text=translated,
                    sumber=sumber_info # Pass source to sender
                )

            result_output.append({
                "channel_link": entry["channel_link"],
                "original_text": msg["text"],
                "id": str(msg["id"]),
                "date": msg["date"]
            })

    if result_output:
        save_results(result_output)

if __name__ == "__main__":
    asyncio.run(main())
