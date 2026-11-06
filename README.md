# WIF Desk — AI Trading Agent on Robinhood Chain

A fully autonomous trading agent that scans, audits, scores, and trades tokens on Robinhood Chain. Built for the World is Flat Hackathon (Agents & AI category).

## Architecture

5-agent pipeline: **Scanner → Auditor → Analyst → Executor → Risk**

- **Scanner**: pulls live Robinhood Chain tokens (DexScreener + on-chain Uniswap V3 pool logs), feeds the pipeline
- **Auditor**: 4-layer safety check (contract, liquidity, pool age, top holders)
- **Analyst**: rules-based scoring (alive, organic, flush, chase) with LLM-ready interface
- **Executor**: position sizing, Telegram push with Buy/Skip buttons, PAPER auto-fill
- **Risk**: stop-loss (6%), trailing stop (12% after +20%), timeout (3h), PnL exits

Every token found is deduped — the same token is never pushed twice.

## Telegram bot

**@grokfomotrading_bot**

| Command | What it does |
|---|---|
| `/start` | Start the bot |
| `/wallet` | Live wallet address + ETH balance |
| `/scan` | Scan for tokens, run the full pipeline |
| `/status` | Tokens scanned, mode, recent tokens |
| `/mode` | Show/set mode (`/mode paper` or `/mode live`) |
| `/practice` | Reset virtual cash (default $1,000) |
| `/trade` | Buy by number/address: `/trade 1 50` or `/trade 1 25%` |
| `/close` | Close a position: `/close 1`, `/close 1 50`, or no args to list |
| `/portfolio` | Cash + open positions |
| `/pnl` | PnL report + bar-chart image |
| `/pause` / `/resume` | Stop/start trade signals |

Trades open with **Close 15% / Close 50% / Close All** buttons. Custom sizing supports USD or a percentage of cash.

## Flywheel

1. Agent detects a new token → scans/audits/scores it
2. If it passes, pushes to Telegram with Buy/Skip buttons
3. User burns $wif to vote on which coins to trade
4. Every executed trade burns a small amount of $wif
5. More trading → more $wif burned → more community engagement → more trading

## Chain details

- Chain: Robinhood Chain (EVM, chain ID 4663)
- RPC: https://rpc.mainnet.chain.robinhood.com
- $wif (RobinWifHat): `0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B`
- WETH: `0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73`
- Uniswap V3 Factory: `0x1f7d7550b1b028f7571e69a784071f0205fd2efa`
- Uniswap V3 Router: `0xcaf681a66d020601342297493863e78c959e5cb2`
- DEX: Uniswap V3 on Robinhood Chain

## Running

```bash
cd wif-desk
pip install -r requirements.txt
python3 main.py
```

Environment (`.env`):

```
TG_TOKEN=...
OPENROUTER_API_KEY=...
OWNER_CHAT_ID=...
RH_RPC_URL=https://rpc.mainnet.chain.robinhood.com
# WALLET_PRIVATE_KEY=0x...   # only for /mode live
```

## Modes

- **PAPER** (default): virtual $1,000 cash, no real funds move. All commands work.
- **LIVE**: real swaps via the Uniswap V3 router. Requires `WALLET_PRIVATE_KEY` set in the environment and an explicit `confirm` on every trade (`/trade 1 50 confirm`). The pipeline never auto-swaps in live mode.

## Storage

State lives in `wif_desk.db` (SQLite): scanned tokens, activity logs, signals, wallets, and trades. Wallets and positions survive restarts.

## Hackathon

Built for the World is Flat Hackathon ($10k prize, Robinhood Chain, Agents & AI category). Submissions close Nov 12, 2026.
