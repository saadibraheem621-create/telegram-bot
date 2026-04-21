import requests
import time
import xml.etree.ElementTree as ET
import os

BOT_TOKEN = os.getenv("8586159632:AAF6aWV9g7kNWkpCVsRE5iy08_SUpFKtj68")
ADMIN_CHAT_ID = os.getenv("5228133825")

TOKEN = "8586159632:AAF6aWV9g7kNWkpCVsRE5iy08_SUpFKtj68"
CHAT_ID = "5228133825"
YOUTUBE_CHANNEL_ID = "@alisaad8080-f1b"

last_video_id = None

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, data=data, timeout=20)
    except Exception as e:
        print("Send message error:", e)

def get_latest_youtube_video():
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL_ID}"
    try:
        response = requests.get(rss_url, timeout=20)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015"
        }

        entry = root.find("atom:entry", ns)
        if entry is None:
            return None, None

        video_id = entry.find("yt:videoId", ns).text
        title = entry.find("atom:title", ns).text
        link = f"https://www.youtube.com/watch?v={video_id}"

        return video_id, f"🎥 فيديو جديد على القناة:\n{title}\n{link}"

    except Exception as e:
        print("YouTube check error:", e)
        return None, None

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {}
    if offset:
        params["offset"] = offset
    try:
        response = requests.get(url, params=params, timeout=20)
        return response.json()
    except Exception as e:
        print("Get updates error:", e)
        return {}

def handle_commands():
    global last_update_id
    data = get_updates(last_update_id)

    if not data.get("ok"):
        return

    for item in data.get("result", []):
        last_update_id = item["update_id"] + 1

        message = item.get("message")
        if not message:
            continue

        text = message.get("text", "")
        chat_id = str(message["chat"]["id"])

        if chat_id != str(CHAT_ID):
            continue

        if text == "/start":
            send_message("✅ البوت شغال.\nالأوامر:\n/check\n/price")
        elif text == "/check":
            send_message("✅ البوت يعمل بشكل طبيعي.")
        elif text == "/price":
            send_message("💵 تنبيه مشروع الدولار: هذه رسالة تجريبية. لاحقاً نربطها بالسعر الحقيقي أو التوقعات.")
        elif text == "/help":
            send_message("الأوامر المتاحة:\n/start\n/check\n/price")

send_message("🚀 تم تشغيل البوت بنجاح.")

last_update_id = None

while True:
    handle_commands()

    video_id, message = get_latest_youtube_video()
    if video_id:
        if last_video_id is None:
            last_video_id = video_id
        elif video_id != last_video_id:
            send_message(message)
            last_video_id = video_id

    time.sleep(60)
