import os
import re
import html
import json
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_BASE = "https://api.telegram.org"
MESSAGE_LIMIT = 4096
CAPTION_LIMIT = 1024 

def render_html_with_basic_md(text: str) -> str:
    if not text: return ""
    token_re = re.compile(
        r'(\[([^\]]+)\]\((https?://[^)\s]+)\)|(\*\*|__)(.+?)\4|(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_))',
        re.DOTALL
    )
    out, i = [], 0
    for m in token_re.finditer(text):
        out.append(html.escape(text[i:m.start()]))
        groups = m.groups()
        if groups[1] and groups[2]:
            out.append(f'<a href="{html.escape(groups[2], quote=True)}">{html.escape(groups[1])}</a>')
        elif groups[3] and groups[4]:
            out.append(f'<b>{html.escape(groups[4])}</b>')
        elif groups[5]:
            out.append(f'<i>{html.escape(groups[5])}</i>')
        elif groups[6]:
            out.append(f'<i>{html.escape(groups[6])}</i>')
        i = m.end()
    out.append(html.escape(text[i:]))
    return "".join(out)

def _split_for_telegram_raw(text: str, limit: int) -> list[str]:
    if not text: return [""]
    if len(text) <= limit: return [text]
    parts, current, cur_len = [], [], 0
    for para in text.split("\n\n"):
        chunk = para + "\n\n"
        if cur_len + len(chunk) <= limit:
            current.append(chunk); cur_len += len(chunk)
        else:
            if current: parts.append("".join(current).rstrip())
            current, cur_len = [chunk], len(chunk)
    if current: parts.append("".join(current).rstrip())
    return parts

def send_telegram_message_html(translated_text: str, sumber: str = None):
    full_text = translated_text or ""
    if sumber:
        full_text += f"\n\n Sumber: {sumber}"
    
    raw_chunks = _split_for_telegram_raw(full_text, MESSAGE_LIMIT)
    results = []
    for raw_chunk in raw_chunks:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": render_html_with_basic_md(raw_chunk), "parse_mode": "HTML"}
        r = requests.post(f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload)
        results.append(r.json())
    return results

def send_photo_to_telegram_channel(image_path: str, translated_caption: str, sumber: str = None):
    raw_caption = translated_caption or ""
    if sumber:
        raw_caption += f"\n\n Sumber: {sumber}"
    
    head_raw = raw_caption[:CAPTION_LIMIT]
    tail_raw = raw_caption[CAPTION_LIMIT:]
    
    with open(image_path, "rb") as f:
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": render_html_with_basic_md(head_raw), "parse_mode": "HTML"}
        r = requests.post(f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data=data, files={"photo": f})
    
    if r.ok and tail_raw:
        send_telegram_message_html(tail_raw)
    return r.json()

def send_media_group_to_telegram(image_paths: list[str], translated_caption: str, sumber: str = None):
    if len(image_paths) == 1:
        return send_photo_to_telegram_channel(image_paths[0], translated_caption, sumber)

    raw_caption = translated_caption or ""
    if sumber:
        raw_caption += f"\n\n Sumber: {sumber}"
    
    head_raw = raw_caption[:CAPTION_LIMIT]
    tail_raw = raw_caption[CAPTION_LIMIT:]
    
    media, files = [], {}
    for i, path in enumerate(image_paths):
        file_key = f"photo_{i}"
        files[file_key] = open(path, "rb")
        item = {"type": "photo", "media": f"attach://{file_key}", "parse_mode": "HTML"}
        if i == 0: item["caption"] = render_html_with_basic_md(head_raw)
        media.append(item)

    payload = {"chat_id": (None, TELEGRAM_CHAT_ID), "media": (None, json.dumps(media))}
    r = requests.post(f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup", files={**files, **payload})
    for f in files.values(): f.close()
    
    if r.ok and tail_raw:
        send_telegram_message_html(tail_raw)
    return r.json()
