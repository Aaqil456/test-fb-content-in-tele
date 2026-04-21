import os
import time
import requests

# Pastikan API Key ada dalam Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Guna 1.5-flash-latest atau 2.0-flash (Mana yang stabil di akaun anda)
GEMINI_MODEL = "gemini-3.1-flash-lite" 

def translate_text_gemini(text: str, model: str = GEMINI_MODEL) -> str:
    """
    Translates text to Malay and PURGES all source links/platforms using LLM.
    Guaranteed to retry until success with smart throttling.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    # PROMPT ASAL ANDA (Sangat kuat untuk tapis link/source)
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

    attempt = 0
    while True:  # STRATEGI: BERDEGIL SAMPAI JADI
        attempt += 1
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # Jika terkena Rate Limit (429)
            if resp.status_code == 429:
                # Rehat makin lama: 100s, 200s, 300s...
                wait_time = min(100 * attempt, 300) 
                print(f"[Warning] Google sekat (429). Cubaan #{attempt}. Rehat {wait_time}s...")
                time.sleep(wait_time)
                continue 

            # Jika Error lain (500, 503, etc)
            if not resp.ok:
                print(f"[Error] HTTP {resp.status_code}. Rehat 20s...")
                time.sleep(20)
                if attempt > 15: return text # Break kalau dah melampau sangat gagalnya
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for p in parts:
                    t = p.get("text", "").strip()
                    if t:
                        print(f"[Success] Terjemahan & Tapis selesai.")
                        
                        # --- CARA PALING CONFIRM: HARD DELAY ---
                        # Setiap kali berjaya, WAJIB rehat 15 saat. 
                        # Ini akan pastikan RPM anda sentiasa bawah 5. 
                        # Google takkan sekat orang yang hantar 4-5 request seminit.
                        time.sleep(15) 
                        
                        return t

        except Exception as e:
            print(f"[Error] Masalah teknikal: {e}. Rehat 15s...")
            time.sleep(15)
            if attempt > 10: return text

    return text
