import asyncio, time
from config import *
import db
import dex

async def _notify(chat_id, text):
    try:
        from telegram import send_msg
        await send_msg(chat_id, text)
    except Exception as e:
        print(f"Risk notify error: {e}")

async def close_position(trade, reason):
    pair = dex.get_best_pair(trade["mint"])
    price = float(pair.get("priceUsd", 0) or 0) if pair else trade["entry_price"]
    res = db.close_trade(trade["id"], price)
    if not res:
        return None
    pnl = res["pnl"]
    sign = "+" if pnl >= 0 else ""
    await _notify(trade["chat_id"],
        f"Risk exit ({reason}) on {trade['name']}\n"
        f"Exit ${price:.6f} · PnL {sign}${pnl:.2f}")
    db.log_activity("risk", trade["mint"], "closed", f"{reason} pnl {pnl:.2f}")
    return res

async def partial_close(trade, fraction, reason="partial"):
    pair = dex.get_best_pair(trade["mint"])
    price = float(pair.get("priceUsd", 0) or 0) if pair else trade["entry_price"]
    res = db.partial_close_trade(trade["id"], fraction, price)
    if not res:
        return None
    pnl = res["pnl"]
    sign = "+" if pnl >= 0 else ""
    await _notify(trade["chat_id"],
        f"{reason} close ({int(fraction*100)}%) on {trade['name']}\n"
        f"Exit ${price:.6f} · PnL {sign}${pnl:.2f}")
    db.log_activity("risk", trade["mint"], "partial_close", f"{fraction} pnl {pnl:.2f}")
    return res

async def risk_loop():
    print("Risk: monitoring positions")
    while True:
        await asyncio.sleep(15)
        try:
            trades = db.get_trades(status="open")
            now = time.time()
            for t in trades:
                pair = dex.get_best_pair(t["mint"])
                price = float(pair.get("priceUsd", 0) or 0) if pair else 0
                if price <= 0:
                    continue
                entry = t["entry_price"]
                pnl_pct = (price - entry) / entry * 100 if entry else 0
                age_h = (now - t["ts"]) / 3600

                stop_pct = DEFAULT_SETTINGS.get("stop_pct", 6)
                trail_activate = DEFAULT_SETTINGS.get("trail_activate_pct", 20)
                trail_pct = DEFAULT_SETTINGS.get("trail_pct", 12)
                timeout_h = DEFAULT_SETTINGS.get("timeout_hours", 3)

                if pnl_pct <= -stop_pct:
                    await close_position(t, f"stop-loss {pnl_pct:.1f}%")
                elif pnl_pct >= trail_activate:
                    trail_price = price * (1 - trail_pct / 100)
                    if price <= trail_price:
                        await close_position(t, f"trailing stop {pnl_pct:.1f}%")
                elif age_h >= timeout_h:
                    await close_position(t, f"timeout {age_h:.1f}h")
        except Exception as e:
            print(f"Risk error: {e}")
