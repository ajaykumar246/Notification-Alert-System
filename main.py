import os
from dotenv import load_dotenv
import json
import requests
from bs4 import BeautifulSoup
load_dotenv()
# =====================================================================
# 1. CONFIGURATION
# =====================================================================
TARGET_URL = "https://apply1.tndge.org/dge-notification/SSLC"
STATE_FILE = "seen_notifications.json"

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Optional Keyword Filter (Leave empty [] to receive ALL notifications)
KEYWORDS = ["SCAN COPY","ANSWER SCRIPTS"]


# =====================================================================
# 2. STATE MANAGEMENT (Prevents Duplicate Alerts)
# =====================================================================
def load_seen_notifications():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return []
    return []


def save_seen_notifications(seen_list):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(seen_list, file, indent=4)


# =====================================================================
# 3. TELEGRAM NOTIFICATION DISPATCHER
# =====================================================================
def send_telegram_alert(title, link):
    message_body = (
        f"🚨 *NEW TNDGE SSLC NOTIFICATION* 🚨\n\n"
        f"📌 *Notice:* {title}\n\n"
        f"🔗 [Click Here to View / Download Document]({link})"
    )
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_body,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(api_url, data=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Notification sent successfully for: {title[:30]}...")
            return True
        else:
            print(f"❌ Telegram API Error ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed connection to Telegram Server: {e}")
        return False


# =====================================================================
# 4. PARSER & EXECUTION ENGINE (UPDATED TO TARGET col-md-8)
# =====================================================================
def main():
    print("🔄 Connecting to TNDGE Portal...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
    except Exception as e:
        print(f"❌ Failed to reach the server network: {e}")
        return

    if response.status_code != 200:
        print(f"❌ Portal returned bad status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    seen_links = load_seen_notifications()
    has_updates = False

    # FIX: Use a CSS selector to explicitly find the ul inside the col-md-8 div.
    # This completely bypasses the col-md-4 sidebar.
    list_container = soup.select_one('div.col-md-8 ul.list-group')
    
    if not list_container:
        print("❌ Could not isolate the notification listing container inside col-md-8.")
        return

    list_items = list_container.find_all('li', class_='list-group-item')
    
    for item in reversed(list_items):
        anchor = item.find('a')
        if not anchor:
            continue
            
        title_text = anchor.get_text().replace("Reg", "").replace("reg", "").strip()
        raw_link = anchor.get('href', '').strip()
        
        if not raw_link:
            continue

        if raw_link.startswith('/'):
            full_link = f"https://apply1.tndge.org{raw_link}"
        else:
            full_link = raw_link

        if full_link not in seen_links:
            if KEYWORDS:
                matches_keyword = any(kw.upper() in title_text.upper() for kw in KEYWORDS)
                if not matches_keyword:
                    seen_links.append(full_link)
                    continue

            print(f"🔔 Match Found: {title_text}")
            
            success = send_telegram_alert(title_text, full_link)
            if success:
                seen_links.append(full_link)
                has_updates = True

    if has_updates:
        save_seen_notifications(seen_links)
        print("💾 History log local sync complete.")
    else:
        print("😴 Check finished. No new updates found.")


if __name__ == "__main__":
    main()