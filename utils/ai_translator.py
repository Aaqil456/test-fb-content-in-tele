import os
import time
import requests

# Pastikan API Key ada dalam Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Menggunakan 1.5-flash-latest untuk kestabilan kuota Free Tier
GEMINI_MODEL = "gemini-2.5-flash-latest" 

def translate_text_gemini(text: str, model: str = GEMINI_MODEL) -> str:
    """
    Translates `text` to Malay using Google Gemini API.
    Kekalkan prompt asal tetapi ditambah logic anti-Rate Limit.
    """
    
    # --- STRATEGI 1: SKIP TEKS TEKNIKAL (JIMAT QUOTA) ---
    # Jika teks cuma crypto pair atau signal pendek, terus pulangkan asal (tak payah panggil API)
    keywords_to_skip = ["MACD", "USDT", "Overbought", "Oversold", "RSI", "crossover", "DUMP", "PUMP"]
    clean_text = text.strip()
    
    if not clean_text:
        return ""
        
    # Jika teks sangat pendek (< 60 char) dan ada keyword teknikal, skip translation
    if any(k in clean_text for k in keywords_to_skip) and len(clean_text) < 60:
        print(f"[Skip] Teks teknikal dikesan: {clean_text[:30]}... Pulangkan asal.")
        return clean_text

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    # PROMPT ASAL ANDA (TIDAK DIUBAH)
    prompt = (
        "Translate the following text into natural, conversational Malaysian Malay.\n\n"
        "### TONE & STYLE:\n"
        "- Use a friendly, relaxed, and 'santai' tone, like a friend sharing info.\n"
        "- Keep it simple and easy to understand.\n"
        "- Avoid exaggerated slang or interjections.\n"
        "- Maintain a clean, neutral, and informative vibe.\n\n"
        "### KEY TERMINOLOGY:\n"
        "- 'Market Events' -> 'Update Pasaran'\n"
        "- 'Top Mindshare Gainers' -> 'Projek Crypto Viral Hari Ini'\n\n"
        "### LINK & SOURCE HANDLING:\n"
        "- STRICTLY REMOVE platform tags and source links.\n"
        "- PURGE call-to-action phrases (e.g., 'Read more').\n"
        "- Exception: 'ref0, ref1' -> 'SUMBER: 0 1'.\n\n"
        "### OUTPUT RULES:\n"
        "- Return ONLY the translated text.\n"
        f"Text:\n{text}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    # --- STRATEGI 2: SMART PERSISTENCE ---
    attempt = 0
    while True: # Terus mencuba sehingga berjaya
        attempt += 1
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # Jika terkena Rate Limit (429)
            if resp.status_code == 429:
                # Tunggu makin lama ikut jumlah cubaan (90s, 180s, 270s...)
                wait_time = min(90 * attempt, 300) 
                print(f"[Warning] Rate Limit (429). Cubaan #{attempt}. Rehat {wait_time}s...")
                time.sleep(wait_time)
                continue 

            # Jika Model Error (404/500)
            if not resp.ok:
                print(f"[Error] HTTP {resp.status_code}: {resp.text[:150]}")
                if attempt > 5: return text # Jika 5x gagal error lain, pulangkan asal
                time.sleep(10)
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for p in parts:
                    t = p.get("text", "").strip()
                    if t:
                        print(f"[Success] Terjemahan selesai.")
                        
                        # --- STRATEGI 3: HARD THROTTLING ---
                        # Rehat 12 saat setiap kali BERJAYA supaya RPM kekal rendah & selamat.
                        time.sleep(12) 
                        
                        return t

        except Exception as e:
            print(f"[Error] Cubaan #{attempt} gagal: {e}")
            if attempt > 10: return text
            time.sleep(10)

    return text
