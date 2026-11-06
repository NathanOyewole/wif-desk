# WIF Desk — World is Flat Hackathon Submission Draft

**Category:** Agents and AI
**Team:** Nathan (solo)
**Bot:** https://t.me/grokfomotrading_bot
**Repo:** https://github.com/NathanOyewole/wif-desk

---

## Project name
WIF Desk

## Tagline
The AI trading agent on Robinhood Chain — scan, audit, score, trade, and burn $wif.

## Description
WIF Desk is a 5-agent autonomous trading agent that runs on Robinhood Chain and lives inside Telegram.

**Pipeline:** Scanner → Auditor → Analyst → Executor → Risk

- **Scanner** finds new tokens (DexScreener + on-chain Uniswap V3 pool logs)
- **Auditor** runs a 4-layer safety check (contract, liquidity, pool age, top holders)
- **Analyst** scores momentum and organic flow (alive / organic / flush / chase)
- **Executor** sizes the position and pushes Buy/Skip to Telegram
- **Risk** applies stop-loss, trailing stop, and timeout exits, and reports PnL

Every trade is paper by default; live mode executes real swaps via the Uniswap V3 router.

## How it uses $wif
- Every executed trade burns $wif (onchain burn to `0x…dEaD`)
- Users burn $wif to vote on which coins the agent should trade
- `/burn` command performs a real onchain $wif burn
- The burn is the proof: real transactions on Robinhood Chain

## Flywheel
1. Agent detects a new token → audits and scores it
2. If it passes, it's pushed to Telegram with Buy/Skip
3. Users burn $wif to vote on trades
4. Every trade burns $wif
5. More trading → more $wif burned → more community engagement → more trading

## Demo
- Bot: https://t.me/grokfomotrading_bot (commands: /scan /trade /portfolio /pnl /burn)
- Demo video: (attach wif-desk-demo.mp4)
- Repo: https://github.com/NathanOyewole/wif-desk

## Commands
/scan · /trade · /close · /portfolio · /pnl · /practice · /mode · /wallet · /burn · /pause

## Notes
- Paper trading is free and open to everyone; live trading is owner-only for safety.
- State (wallets, trades, signals) is persisted in SQLite.
- Built for the World is Flat Hackathon (Agents & AI category).
