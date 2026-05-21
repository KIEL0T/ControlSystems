import os
import time
import threading
import requests
from flask import Flask, request
from dotenv import load_dotenv
from openai import OpenAI

app = Flask(__name__)
load_dotenv(".env")

# =====================
# CONFIGURATION & STATE
# =====================
latest_power = 0.0
total_wh = 0.0
last_time = time.time()

PRICE_PER_KWH = 12.0
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OFFSET_FILE = "offset.txt"

LM_URL = os.getenv("LM_STUDIO_URL") or "http://127.0.0.1:1234/v1"
LM_MODEL = os.getenv("LM_STUDIO_MODEL") or "qwen/qwen3.5-9b"
client = OpenAI(base_url=LM_URL, api_key="lm-studio")

# Memory cache to prevent processing the same ID twice within the current session
processed_messages = set()

def get_energy_context():
    global latest_power, total_wh, PRICE_PER_KWH
    current_kwh = total_wh / 1000.0
    accumulated_bill = current_kwh * PRICE_PER_KWH
    projected_monthly_bill = ((latest_power * 24 * 30) / 1000.0) * PRICE_PER_KWH
    return (
        f"REAL-TIME ELECTRICAL DATA:\n"
        f"- Current live power draw: {latest_power:.2f} Watts\n"
        f"- Accumulated bill right now: ₱{accumulated_bill:.2f}\n"
        f"- Estimated 30-day monthly bill: ₱{projected_monthly_bill:.2f}\n"
    )

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print(f"📡 Telegram Send Status: {r.status_code}")
    except Exception as e: 
        print("❌ Telegram transmission error:", e)

def load_offset():
    try:
        if os.path.exists(OFFSET_FILE):
            with open(OFFSET_FILE, "r") as f: 
                val = int(f.read().strip())
                print(f"💾 Loaded offset from file: {val}")
                return val
    except Exception as e:
        print(f"⚠️ Failed to read offset file: {e}")
    return 0

def save_offset(value):
    try:
        with open(OFFSET_FILE, "w") as f: 
            f.write(str(value))
            f.flush()
        print(f"💾 Saved new offset to disk: {value}")
    except Exception as e:
        print(f"❌ CRITICAL: Could not write to offset.txt: {e}")

# ======================
# ESP32 DATA RECEIVER
# ======================
@app.route('/data', methods=['POST'])
def data():
    global latest_power, total_wh, last_time
    raw = request.values.get("power")
    if raw is None: return "NO DATA"
    try: power = float(raw)
    except: power = 0.0
    latest_power = power
    now = time.time()
    hours = (now - last_time) / 3600.0
    last_time = now
    total_wh += power * hours
    return "OK"

# ==========================================
# DIAGNOSTIC REASONING LOOP
# ==========================================
def agentic_loop():
    global processed_messages
    offset = load_offset()
    print(f"\n🚀 System running. Connecting to LM Studio at: {LM_URL}")

    while True:
        # We enforce a dynamic offset parameter inside the GET string
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset + 1}&timeout=5"
        try:
            res = requests.get(url).json()
        except Exception as e:
            print(f"⚠️ Network check failed (retrying in 3s): {e}")
            time.sleep(3)
            continue

        results = res.get("result", [])
        if results:
            print(f"📥 Telegram packet received! Contains {len(results)} raw messages.")

        for update in results:
            update_id = update["update_id"]

            # Double-guard check: Verify both against memory cache and offset tracking values
            if update_id <= offset or update_id in processed_messages:
                print(f"⏭️ Skipping duplicate message ID: {update_id}")
                continue

            # Lock the message instantly to prevent double-processing
            processed_messages.add(update_id)
            offset = update_id
            save_offset(offset)

            if "message" not in update or "text" not in update["message"]:
                continue

            user_message = update["message"]["text"]
            print(f"\n👤 Active User Message: '{user_message}' [ID: {update_id}]")
            print("🤖 Forwarding request to local Qwen instance... please wait...")

            live_data_context = get_energy_context()

            try:
                response = client.chat.completions.create(
                    model=LM_MODEL,
                    messages=[
                        {"role": "system", "content": (
                            "You are a smart Home Energy Management Agent running locally. "
                            "Answer conversationally and naturally in English or Taglish based on this dataset:\n"
                            f"{live_data_context}"
                        )},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.4
                )
                
                reply = response.choices[0].message.content
                print(f"🤖 Qwen Gen complete. Sending response back to Telegram.")
                send_telegram(reply)
                
            except Exception as e:
                print("⚠️ Local AI Processing Error:", e)
                send_telegram("Pasensya na, nagkaroon ng error ang AI server ko.")

        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=agentic_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)