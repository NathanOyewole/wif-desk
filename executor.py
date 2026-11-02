import asyncio, httpx, json, time
from config import *
import db

async def send_telegram(chat_id, text, buttons=None):
    async with httpx.AsyncClient(timeout=15) as client:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        r = await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json=payload)
        return r.json()

async def execute(address, name, analyst_result, scanner_data):
    settings = DEFAULT_SETTINGS
    stack = settings.get("stack", 200.0)
    mode = settings.get("mode", "PAPER")
    size_pct = settings.get("executor_size_pct", 8)
    min_trade = settings.get("min_trade_size", 10.0)

    pair = scanner_data.get("pair", {})
    price = float(pair.get("priceUsd", 0) or 0)
    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)

    raw_size = stack * (size_pct / 100.0)
    if liq:
        cap = liq * 0.02
        raw_size = min(raw_size, cap)

    if raw_size < min_trade:
        if settings.get("below_min_action") == "bump":
            raw_size = min_trade
        else:
            db.log_activity("executor", address, "skipped", "under min")
            return {"status": "skipped", "reason": "under min"}

    size_usd = round(raw_size, 2)
    stack_pct = round(size_usd / stack * 100, 1)
    score = analyst_result.get("score", 0)

    link = f"https://dexscreener.com/robinhood/{address}"
    paper_prefix = "PAPER · " if mode == "PAPER" else ""
    text = (f"{paper_prefix}Buy {name} · ${size_usd:.2f} · {stack_pct}% of stack\n"
            f"Auditor 4/4 · Analyst {score} · $wif burn on trade")
    buttons = [[{"text": "Buy on DexScreener", "url": link},
                {"text": "Bought", "callback_data": f"bought:{address}"},
                {"text": "Skip", "callback_data": f"skip:{address}"}]]
    await send_telegram(OWNER_CHAT_ID, text, buttons)

    db.log_activity("executor", address, "pushed", f"${size_usd} · {link}")
    return {"agent": "executor", "mint": address, "signalPrice": price, "sizeUsd": size_usd,
            "stackPct": stack_pct, "link": link, "mode": mode, "status": "sent"}
