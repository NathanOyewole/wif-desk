import asyncio, httpx, json, time
from config import *

async def poll_telegram():
    offset = 0
    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                r = await client.get(f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates", params={"offset": offset, "timeout": 30})
                data = r.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")
                    if text.startswith("/"):
                        await handle_command(chat_id, text)
                    cb = update.get("callback_query", {})
                    if cb:
                        await handle_callback(cb)
        except Exception as e:
            print(f"Telegram poll error: {e}")
            await asyncio.sleep(5)
        await asyncio.sleep(1)

async def handle_command(chat_id, text):
    parts = text.split()
    cmd = parts[0].lower()
    if cmd == "/start":
        await send_msg(chat_id, "WIF Desk online. Robinhood Chain trading agent.\nCommands: /status /pause /resume /mode")
    elif cmd == "/status":
        import db
        coins = db.get_db().execute("SELECT count(*) FROM coins").fetchone()[0]
        await send_msg(chat_id, f"Tokens scanned: {coins}\nMode: {DEFAULT_SETTINGS.get('mode', 'PAPER')}")
    elif cmd == "/pause":
        await send_msg(chat_id, "Paused.")
    elif cmd == "/resume":
        await send_msg(chat_id, "Resumed.")
    elif cmd == "/mode":
        if len(parts) > 1:
            await send_msg(chat_id, f"Mode set to {parts[1].upper()}")
    else:
        await send_msg(chat_id, f"Unknown command: {cmd}")

async def handle_callback(cb):
    cb_id = cb.get("id")
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id})

async def send_msg(chat_id, text, buttons=None):
    async with httpx.AsyncClient(timeout=15) as client:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json=payload)
