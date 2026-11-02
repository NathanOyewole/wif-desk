# WIF Desk — AI Trading Agent on Robinhood Chain

A fully autonomous trading agent that scans, audits, scores, and trades tokens on Robinhood Chain. Users burn $wif to vote on which coins the agent should trade. Every trade burns $wif, creating a flywheel.

## Architecture

5-agent pipeline: Scanner → Auditor → Analyst → Executor → Risk

- **Scanner**: Monitors Uniswap V3 pool creation events on Robinhood Chain
- **Auditor**: 4-layer safety check (contract, liquidity, pool age, top holders)
- **Analyst**: LLM scoring (alive, organic, flush, chase) via OpenRouter
- **Executor**: Position sizing, Telegram push with buttons, PAPER auto-fill
- **Risk**: Stop-loss, trailing stop, timeout exits, PnL tracking

## Flywheel

1. Agent detects new token → scans/audits/scores it
2. If passed, pushes to Telegram with [Buy] [Skip] buttons
3. User burns $wif to vote on which coins to trade
4. Every executed trade burns a small amount of $wif
5. More trading → more $wif burned → more community engagement → more trading

## Chain Details

- Chain: Robinhood Chain (EVM, chain ID 4663)
- RPC: https://rpc.mainnet.chain.robinhood.com
- $wif (RobinWifHat): 0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B
- Uniswap V3 Factory: 0x1f7d7550b1b028f7571e69a784071f0205fd2efa
- DEX: Uniswap V3 on Robinhood Chain

## Running

```bash
cd wif-desk
python3 main.py
```

## Hackathon

Built for the World is Flat Hackathon ($10k prize, Robinhood Chain, Agents & AI category).
Submissions close Nov 12, 2026.
