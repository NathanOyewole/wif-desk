# WIF Desk — BD Team Trial Guide

**Bot:** [@grokfomotrading_bot](https://t.me/grokfomotrading_bot)
**Chain:** Robinhood Chain (EVM, chain ID 4663)
**Mode:** PAPER trading (virtual cash, no real funds)

---

## 1. Start the bot

Open the bot link above and tap **Start** (or send `/start`).

You'll get:
```
WIF Desk online. Robinhood Chain trading agent.
Commands: /scan /status /trade /portfolio /practice /mode
```

## 2. Run a scan

```
/scan
```

The **Scanner agent** pulls live Robinhood Chain tokens (DexScreener + on-chain pool logs) and feeds them through the full pipeline:

```
Scanner → Auditor → Analyst → Executor → Risk
```

You'll see a numbered list:
```
1. Robinhood (ROBINHOOD) — 0x008Df4...
2. Robinhood (ROBINHOOD) — 0x79Fe86...
...
```

## 3. Set up your practice wallet

```
/practice
```
Resets your virtual balance to **$1,000**. You can also set a custom amount:
```
/practice 5000
```

## 4. Buy a token

Use the number from the `/scan` list:
```
/trade 1 50
```
Or use a percentage of your cash:
```
/trade 1 25%
```

The **Auditor** (contract / liquidity / pool age / holders) and **Analyst** (alive / organic / flush / chase score) run before the trade. If a token fails the gates, the bot tells you why. Add `force` to override:
```
/trade 1 50 force
```

After buying you'll see buttons:
```
[Close 15%] [Close 50%] [Close All]   [View on DexScreener]
```

## 5. Manage positions

- **Close part of a trade** — tap **Close 15%**, **Close 50%**, or **Close All**
- **Close by command** — `/close 1` (100%) or `/close 1 50` (50%)
- **View portfolio** — `/portfolio` (cash + open positions)
- **View PnL** — `/pnl` (report + bar-chart image of every trade)

## 6. Other commands

| Command | What it does |
|---|---|
| `/scan` | Scan for tokens, run the full pipeline |
| `/status` | Tokens scanned, mode, recent tokens |
| `/mode` | Show/set mode (`/mode paper` or `/mode live`) |
| `/practice` | Reset virtual cash |
| `/trade` | Buy by number/address, custom size |
| `/close` | Close a position (optionally partial) |
| `/portfolio` | Cash + open positions |
| `/pnl` | PnL report + chart |
| `/pause` / `/resume` | Pause/resume trading |

## 7. How the 5-agent pipeline works

1. **Scanner** — finds new tokens on Robinhood Chain
2. **Auditor** — 4-layer safety check (contract, liquidity, pool age, top holders)
3. **Analyst** — scores momentum/organic activity (rules-based)
4. **Executor** — sizes the position, pushes Buy/Skip to Telegram
5. **Risk** — stop-loss (6%), trailing stop (12% after +20%), timeout (3h), PnL exits

Every trade is paper-only. No real funds move.

## 8. Notes

- Your wallet/positions are stored server-side and survive restarts.
- Trade alerts are broadcast to everyone who `/start`s the bot.
- The bot runs on Robinhood Chain mainnet data.
- For the hackathon: built for the World is Flat Hackathon (Agents & AI category).
