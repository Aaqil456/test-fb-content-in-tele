from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

async def fetch_latest_messages(api_id, api_hash, channel_username, limit=10):
    client = TelegramClient("telegram_session", api_id, api_hash)
    await client.start()
    
    messages = []
    # Dictionary to group media by their grouped_id
    media_groups = {}

    async for message in client.iter_messages(channel_username, limit=limit):
        has_photo = isinstance(message.media, MessageMediaPhoto)
        
        # If it's part of an album
        if message.grouped_id:
            if message.grouped_id not in media_groups:
                media_groups[message.grouped_id] = {
                    "id": message.id,
                    "text": message.text or "",
                    "photos": [],
                    "date": str(message.date),
                    "raw": message
                }
            
            if has_photo:
                media_groups[message.grouped_id]["photos"].append(message.media)
            
            # Ensure we capture the caption (usually only one message in the group has it)
            if message.text and not media_groups[message.grouped_id]["text"]:
                media_groups[message.grouped_id]["text"] = message.text
        
        else:
            # Standard single message handling
            if message.text or has_photo:
                messages.append({
                    "id": message.id,
                    "text": message.text or "",
                    "has_photo": has_photo,
                    "photos": [message.media] if has_photo else [],
                    "raw": message,
                    "date": str(message.date)
                })

    # Add the grouped albums to the final list
    for g_id in media_groups:
        messages.append(media_groups[g_id])

    await client.disconnect()
    # Sort by ID to keep chronological order
    return sorted(messages, key=lambda x: x["id"])
