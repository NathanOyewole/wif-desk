import asyncio, httpx, json, time
from config import *
import db

active_chats = set()
last_lists = {}

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

def _resolve_token(chat_id, ref):
    if ref.isdigit():
        idx = int(ref) - 1
        lst = last_lists.get(chat_id) or []
        if idx < 0 or idx >= len(lst):
            return None
        return lst[idx]
    return ref

async def _gates(address):
    """Run the Auditor + Analyst agents on a token. Returns (passed, audit, analysis)."""
    import auditor, analyst
    scanner_data = {"mint": address, "pair": None}
    a = await auditor.audit(address, scanner_data)
    if not a["passed"]:
        return False, a, None
    an = await analyst.analyze(address, scanner_data, a)
    return an["passed"], a, an

async def handle_command(chat_id, text):
    active_chats.add(chat_id)
    parts = text.split()
    cmd = parts[0].lower()
    if cmd == "/start":
        await send_msg(chat_id, "WIF Desk online. Robinhood Chain trading agent.\nCommands: /scan /status /trade /portfolio /practice /mode")
    elif cmd == "/scan":
        import scanner
        await send_msg(chat_id, "Scanning Robinhood Chain (Scanner agent)...")
        found = await scanner.scan_once()
        conn = db.get_db()
        rows = conn.execute("SELECT address, name, symbol FROM coins ORDER BY ts DESC LIMIT 12").fetchall()
        if not rows:
            await send_msg(chat_id, "No tokens found yet.")
            return
        last_lists[chat_id] = [r[0] for r in rows]
        lines = [f"Scanner found {len(found)} tokens. Pipeline (Auditor→Analyst→Executor) is running..."]
        for i, r in enumerate(rows, 1):
            lines.append(f"{i}. {r['name']} ({r['symbol']}) — {r['address'][:10]}...")
        lines.append("\nUse /trade <number> <usd> to buy.")
        await send_msg(chat_id, "\n".join(lines))
    elif cmd == "/status":
        conn = db.get_db()
        coins = conn.execute("SELECT count(*) FROM coins").fetchone()[0]
        open_trades = len(db.get_trades(chat_id, "open"))
        rows = conn.execute("SELECT address, name, symbol FROM coins ORDER BY ts DESC LIMIT 5").fetchall()
        msg = f"Tokens scanned: {coins}\nMode: {DEFAULT_SETTINGS.get('mode', 'PAPER')}\nOpen positions: {open_trades}"
        if rows:
            last_lists[chat_id] = [r[0] for r in rows]
            msg += "\n\nRecent:\n" + "\n".join(f"{i}. {r['name']} ({r['symbol']})" for i, r in enumerate(rows, 1))
        await send_msg(chat_id, msg)
    elif cmd in ("/signals", "/signal"):
        conn = db.get_db()
        rows = conn.execute("SELECT mint,name,price_usd,size_usd,link,ts FROM signals ORDER BY id DESC LIMIT 10").fetchall()
        if not rows:
            await send_msg(chat_id, "No signals yet.")
            return
        lines = ["Recent signals:"]
        for r in rows:
            lines.append(f"{r[1] or r[0][:8]} · ${r[3]:.2f} @ ${r[2]:.6f}\n{r[4]}")
        # recent rejections
        rej = conn.execute("SELECT mint,detail FROM activity WHERE action='rejected' ORDER BY id DESC LIMIT 5").fetchall()
        if rej:
            lines.append("\nRecent rejections:")
            for r in rej:
                lines.append(f"{r[0][:10]}... — {r[1]}")
        await send_msg(chat_id, "\n".join(lines))
    elif cmd == "/portfolio":
        cash = db.get_wallet(chat_id)
        trades = db.get_trades(chat_id, "open")
        lines = [f"Cash: ${cash:.2f}", f"Open positions: {len(trades)}"]
        for t in trades:
            lines.append(f"{t['name']} · ${t['size_usd']:.2f} @ ${t['entry_price']:.6f}")
        await send_msg(chat_id, "\n".join(lines))
    elif cmd == "/practice":
        if len(parts) > 1:
            try:
                db.set_wallet(chat_id, float(parts[1]))
            except ValueError:
                await send_msg(chat_id, "Usage: /practice [amount]")
                return
        cash = db.get_wallet(chat_id)
        await send_msg(chat_id, f"Practice wallet reset: ${cash:.2f} virtual cash. Paper trades only — no real funds.")
    elif cmd == "/trade":
        if len(parts) < 3:
            await send_msg(chat_id, "Usage: /trade <number|address> <usd|%> [force]\nExamples: /trade 1 50 · /trade 1 25%")
            return
        token = _resolve_token(chat_id, parts[1])
        if not token:
            await send_msg(chat_id, "Unknown token number. Run /scan to refresh the list.")
            return
        cash = db.get_wallet(chat_id)
        size_ref = parts[2]
        try:
            if size_ref.endswith("%"):
                amount = cash * float(size_ref[:-1]) / 100.0
            else:
                amount = float(size_ref)
        except ValueError:
            await send_msg(chat_id, "Amount must be a number or percentage (e.g. 50 or 25%).")
            return
        force = len(parts) > 3 and parts[3].lower() == "force"
        if amount <= 0 or amount > cash:
            await send_msg(chat_id, f"Invalid size. Available cash: ${cash:.2f}")
            return
        import dex
        pair = dex.get_best_pair(token)
        price = float(pair.get("priceUsd", 0) or 0) if pair else 0
        if price <= 0:
            await send_msg(chat_id, f"No price found for {token[:8]}... Try another token or check the address.")
            return
        # Run Auditor + Analyst gates
        passed, audit, analysis = await _gates(token)
        if not passed and not force:
            reasons = []
            for layer in audit.get("layers", []):
                if not layer.get("pass"):
                    reasons.append(f"{layer['name']}: {layer.get('value')}")
            if analysis and analysis.get("failed"):
                reasons += analysis["failed"]
            await send_msg(chat_id, "Trade blocked by gates:\n- " + "\n- ".join(reasons or ["analyst rejected"]))
            return
        mode = DEFAULT_SETTINGS.get("mode", "PAPER")
        if mode == "LIVE":
            if str(chat_id) != str(OWNER_CHAT_ID):
                await send_msg(chat_id, "Live trading is restricted to the bot owner. You can practice in PAPER mode.")
                return
            confirm = len(parts) > 3 and parts[3].lower() in ("confirm", "force")
            if not confirm:
                await send_msg(chat_id, f"LIVE mode: send /trade {parts[1]} {parts[2]} confirm to execute a real swap.")
                return
            try:
                import wallet, swap
                if not wallet.is_configured():
                    await send_msg(chat_id, "Live wallet not configured.")
                    return
                pair = dex.get_best_pair(token)
                price_native = float(pair.get("priceNative", 0) or 0) if pair else 0
                eth_price = (price / price_native) if price_native > 0 else 0
                if eth_price <= 0:
                    await send_msg(chat_id, "Could not determine ETH price.")
                    return
                eth_amount = amount / eth_price
                amount_in_wei = int(eth_amount * 10**18)
                tx_hash, pool, fee = swap.swap_eth_for_token(token, amount_in_wei)
                await send_msg(chat_id, f"LIVE swap sent: {tx_hash.hex()}\nPool {pool} · fee {fee}")
                db.log_activity("executor", token, "live_swap", f"{eth_amount:.6f} ETH · {tx_hash.hex()}")
                return
            except Exception as e:
                await send_msg(chat_id, f"Live swap failed: {e}")
                return
        qty = amount / price
        db.adjust_wallet(chat_id, -amount)
        db.open_trade(chat_id, token, token[:8], price, qty, amount, mode)
        link = f"https://dexscreener.com/robinhood/{token}"
        buttons = [[{"text": "Close 15%", "callback_data": f"close15:{token}"},
                    {"text": "Close 50%", "callback_data": f"close50:{token}"},
                    {"text": "Close All", "callback_data": f"closeall:{token}"}],
                   [{"text": "View on DexScreener", "url": link}]]
        gate_note = " (forced)" if force and not passed else ""
        await send_msg(chat_id, f"Bought {qty:.4f} {token[:8]}... at ${price:.6f} (${amount:.2f}){gate_note}\nCash left: ${db.get_wallet(chat_id):.2f}", buttons)
    elif cmd == "/close":
        if len(parts) < 2:
            trades = db.get_trades(chat_id, "open")
            if not trades:
                await send_msg(chat_id, "No open positions.")
                return
            lines = ["Open positions:"]
            for i, t in enumerate(trades, 1):
                lines.append(f"{i}. {t['name']} · ${t['size_usd']:.2f} @ ${t['entry_price']:.6f}")
            lines.append("\nClose with /close <number> [15|50|100]")
            await send_msg(chat_id, "\n".join(lines))
            return
        token = _resolve_token(chat_id, parts[1])
        if not token:
            await send_msg(chat_id, "Unknown token number. Run /scan to refresh the list.")
            return
        frac = 1.0
        if len(parts) > 2:
            try:
                frac = float(parts[2]) / 100.0
            except ValueError:
                frac = 1.0
        t = db.get_open_trade(chat_id, token)
        if not t:
            await send_msg(chat_id, "No open position for that token.")
            return
        import risk
        if frac >= 0.999:
            res = await risk.close_position(t, "manual close")
        else:
            res = await risk.partial_close(t, frac, "manual partial")
        if res:
            await send_msg(chat_id, f"Closed {int(frac*100)}% of {t['name']} at ${res['exit_price']:.6f}\nPnL: ${res['pnl']:.2f}\nCash: ${db.get_wallet(chat_id):.2f}")
    elif cmd == "/pnl":
        closed = db.get_trades(chat_id, "closed")
        open_trades = db.get_trades(chat_id, "open")
        cash = db.get_wallet(chat_id)
        if not closed:
            await send_msg(chat_id, f"No closed trades yet.\nCash: ${cash:.2f}\nOpen: {len(open_trades)}")
            return
        total = sum(t.get("pnl") or 0 for t in closed)
        wins = [t for t in closed if (t.get("pnl") or 0) > 0]
        losses = [t for t in closed if (t.get("pnl") or 0) <= 0]
        win_rate = len(wins) / len(closed) * 100
        sign = "+" if total >= 0 else ""
        summary = (f"PnL Report\n"
                   f"Total PnL: {sign}${total:.2f}\n"
                   f"Trades: {len(closed)} ({len(wins)}W / {len(losses)}L)\n"
                   f"Win rate: {win_rate:.0f}%\n"
                   f"Cash: ${cash:.2f}")
        img = make_pnl_chart(closed)
        if img:
            await send_photo(chat_id, img, summary)
        else:
            await send_msg(chat_id, summary)
    elif cmd == "/pause":
        from config import RUNTIME
        RUNTIME["paused"] = True
        await send_msg(chat_id, "Paused — no new trade signals will be pushed. /resume to continue.")
    elif cmd == "/resume":
        from config import RUNTIME
        RUNTIME["paused"] = False
        await send_msg(chat_id, "Resumed — signals active.")
    elif cmd == "/burn":
        if str(chat_id) != str(OWNER_CHAT_ID):
            await send_msg(chat_id, "Burning is owner-only.")
            return
        try:
            import wallet, swap
            if not wallet.is_configured():
                await send_msg(chat_id, "Live wallet not configured.")
                return
            amount = float(parts[1]) if len(parts) > 1 else 100.0
            decimals = swap.wif_decimals()
            bal = swap.wif_balance()
            amount_wei = int(amount * (10 ** decimals))
            # If not enough $wif but we have ETH, swap ETH -> $wif first
            if amount_wei > bal:
                eth_bal = wallet.balance_wei()
                if eth_bal <= 0:
                    await send_msg(chat_id, f"Insufficient $wif balance: {bal / (10 ** decimals):.4f} (and no ETH to swap)")
                    return
                # swap up to the USD equivalent of our ETH balance (leave a little for gas)
                import dex
                wif_pair = dex.get_best_pair(swap.WIF_ADDRESS)
                price = float(wif_pair.get("priceUsd", 0) or 0) if wif_pair else 0
                if price <= 0:
                    await send_msg(chat_id, "Could not fetch $wif price for swap.")
                    return
                eth_price = float(wif_pair.get("priceNative", 0) or 0)
                eth_usd = (price / eth_price) if eth_price > 0 else 0
                if eth_usd <= 0:
                    await send_msg(chat_id, "Could not determine ETH price.")
                    return
                spend_usd = min(amount / price, (eth_bal / 10**18) * eth_usd * 0.95)
                if spend_usd <= 0:
                    await send_msg(chat_id, "Not enough ETH to buy $wif.")
                    return
                spend_eth = int((spend_usd / eth_usd) * 10**18)
                await send_msg(chat_id, f"Swapping ${spend_usd:.2f} of ETH → $wif...")
                try:
                    h, pool, fee = swap.swap_eth_for_token(swap.WIF_ADDRESS, spend_eth)
                    wallet.wait_receipt(h)
                except Exception as e:
                    await send_msg(chat_id, f"Swap failed: {e}")
                    return
                bal = swap.wif_balance()
            burn_wei = min(amount_wei, bal)
            if burn_wei <= 0:
                await send_msg(chat_id, "No $wif to burn after swap.")
                return
            tx = swap.burn_wif(burn_wei)
            burned = burn_wei / (10 ** decimals)
            await send_msg(chat_id, f"Burned {burned:,.2f} $wif → 0x...dEaD\nTx: {tx.hex()}")
            db.log_activity("burn", swap.WIF_ADDRESS, "burn", f"{burned} $wif · {tx.hex()}")
        except Exception as e:
            await send_msg(chat_id, f"Burn failed: {e}")
    elif cmd == "/wallet":
        if str(chat_id) != str(OWNER_CHAT_ID):
            await send_msg(chat_id, "Wallet info is owner-only.")
            return
        try:
            import wallet
            if not wallet.is_configured():
                await send_msg(chat_id, "Live wallet not configured. Set WALLET_PRIVATE_KEY in the environment.")
            else:
                bal = wallet.balance_eth()
                await send_msg(chat_id, f"Live wallet: {wallet.address()}\nBalance: {bal:.6f} ETH")
        except Exception as e:
            await send_msg(chat_id, f"Wallet error: {e}")
    elif cmd == "/mode":
        if len(parts) > 1:
            DEFAULT_SETTINGS["mode"] = parts[1].upper()
            await send_msg(chat_id, f"Mode set to {DEFAULT_SETTINGS['mode']}")
        else:
            await send_msg(chat_id, f"Current mode: {DEFAULT_SETTINGS.get('mode', 'PAPER')}")
    else:
        await send_msg(chat_id, f"Unknown command: {cmd}")

async def handle_callback(cb):
    cb_id = cb.get("id")
    data = cb.get("data", "")
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    if data.startswith("bought:"):
        rest = data.split(":", 1)[1]
        mint = rest.split(":")[0]
        size = float(rest.split(":")[1]) if ":" in rest else 0
        import dex
        pair = dex.get_best_pair(mint)
        price = float(pair.get("priceUsd", 0) or 0) if pair else 0
        cash = db.get_wallet(chat_id)
        if size <= 0 or price <= 0:
            await send_msg(chat_id, "Could not open position (no price/size).")
        elif size > cash:
            await send_msg(chat_id, f"Insufficient cash (${cash:.2f}) for ${size:.2f} position.")
        else:
            qty = size / price
            db.adjust_wallet(chat_id, -size)
            db.open_trade(chat_id, mint, mint[:8], price, qty, size, DEFAULT_SETTINGS.get("mode", "PAPER"))
            buttons = [[{"text": "Close 15%", "callback_data": f"close15:{mint}"},
                        {"text": "Close 50%", "callback_data": f"close50:{mint}"},
                        {"text": "Close All", "callback_data": f"closeall:{mint}"}]]
            await send_msg(chat_id, f"Position opened for {mint[:8]}... (${size:.2f} @ ${price:.6f})\nCash: ${db.get_wallet(chat_id):.2f}", buttons)
    elif data.startswith("close15:") or data.startswith("close50:") or data.startswith("closeall:"):
        token = data.split(":", 1)[1]
        frac = {"close15:": 0.15, "close50:": 0.50, "closeall:": 1.0}[data.split(":",1)[0] + ":"]
        t = db.get_open_trade(chat_id, token)
        if t:
            import risk
            res = await risk.partial_close(t, frac, "partial")
            if res:
                await send_msg(chat_id, f"Closed {int(frac*100)}% of {t['name']} at ${res['exit_price']:.6f}\nPnL: ${res['pnl']:.2f}\nCash: ${db.get_wallet(chat_id):.2f}")
        else:
            await send_msg(chat_id, "No open position for that token.")
    elif data.startswith("close:"):
        token = data.split(":", 1)[1]
        t = db.get_open_trade(chat_id, token)
        if t:
            import risk
            res = await risk.close_position(t, "manual close")
            if res:
                await send_msg(chat_id, f"Closed {t['name']} at ${res['exit_price']:.6f}\nPnL: ${res['pnl']:.2f}\nCash: ${db.get_wallet(chat_id):.2f}")
        else:
            await send_msg(chat_id, "No open position for that token.")
    elif data.startswith("skip:"):
        mint = data.split(":", 1)[1]
        await send_msg(chat_id, f"Skipped {mint[:8]}...")
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id})

def make_pnl_chart(trades, path="/tmp/wif_pnl.png"):
    try:
        from PIL import Image, ImageDraw, ImageFont
        W, H = 900, 480
        img = Image.new("RGB", (W, H), "#0b0f14")
        d = ImageDraw.Draw(img)
        try:
            f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except Exception:
            f = fs = ImageFont.load_default()
        d.text((20, 16), "WIF Desk — Trade PnL", font=f, fill="#f5f7fa")
        pnls = [t.get("pnl") or 0 for t in trades]
        max_abs = max([abs(p) for p in pnls] + [1])
        n = len(pnls)
        bar_w = max(20, (W - 80) // max(n, 1) - 8)
        base_y = 260
        for i, (t, p) in enumerate(zip(trades, pnls)):
            x = 40 + i * (bar_w + 8)
            h = int(abs(p) / max_abs * 160)
            color = "#2ea043" if p >= 0 else "#f85149"
            if p >= 0:
                d.rectangle((x, base_y - h, x + bar_w, base_y), fill=color)
            else:
                d.rectangle((x, base_y, x + bar_w, base_y + h), fill=color)
            label = (t.get("name") or "?")[:6]
            d.text((x, base_y + 180), label, font=fs, fill="#9aa4b2")
            d.text((x, base_y + 200), f"{p:+.2f}", font=fs, fill=color)
        d.line((30, base_y, W - 30, base_y), fill="#30363d", width=2)
        img.save(path)
        return path
    except Exception as e:
        print(f"chart error: {e}")
        return None

async def send_photo(chat_id, path, caption=None):
    async with httpx.AsyncClient(timeout=30) as client:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        with open(path, "rb") as fh:
            await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                              data=data, files={"photo": fh})

async def send_msg(chat_id, text, buttons=None):
    async with httpx.AsyncClient(timeout=15) as client:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        await client.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json=payload)
