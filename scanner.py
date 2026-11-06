import asyncio, time, json
from config import *
from rpc import eth_get_code
import db
import bus as bus_mod

# Uniswap V3 PoolCreated event signature
POOL_CREATED_TOPIC = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
LAST_BLOCK = 0
SEEN = set()

async def get_latest_block():
    import httpx
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(RH_RPC_URL, json=payload)
        return int(r.json().get("result", "0x0"), 16)

async def get_logs(from_block, to_block):
    import httpx
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "eth_getLogs",
        "params": [{"fromBlock": hex(from_block), "toBlock": hex(to_block),
                    "address": UNI_V3_FACTORY, "topics": [POOL_CREATED_TOPIC]}]
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(RH_RPC_URL, json=payload)
        return r.json().get("result", [])

def _push_token(token, pair=None):
    """Feed a token into the 5-agent pipeline (Scanner -> bus -> Auditor)."""
    name = token.get("name") or "Unknown"
    symbol = token.get("symbol") or "???"
    address = token.get("address")
    if not address:
        return None
    if address.lower() in SEEN:
        return None
    SEEN.add(address.lower())
    price = token.get("priceUsd") or (pair or {}).get("priceUsd") or "0"
    liq = token.get("liquidity_usd") or (pair or {}).get("liquidity", {}).get("usd", 0)
    db.save_coin(address, name, symbol, liq, str(price))
    bus_mod.bus.scanner_to_auditor.put_nowait({
        "mint": address, "name": name, "symbol": symbol,
        "liquidity_usd": liq, "price_usd": str(price), "pair": pair,
    })
    return address

async def scan_once(blocks_back=200):
    """Scan for tokens: DexScreener (primary) + on-chain PoolCreated logs (secondary).
    Every token found is pushed into the pipeline. Returns list of token addresses."""
    found = []
    # --- Primary source: DexScreener (live Robinhood Chain tokens) ---
    try:
        import dex
        tokens = dex.search_tokens("robinhood", 12)
        for t in tokens:
            addr = _push_token(t)
            if addr:
                found.append(addr)
    except Exception as e:
        print(f"Scanner (dexscreener) error: {e}")

    # --- Secondary source: on-chain PoolCreated logs ---
    global LAST_BLOCK
    try:
        current = await get_latest_block()
        start = max(LAST_BLOCK + 1, current - blocks_back)
        if start <= current:
            logs = await get_logs(start, current)
            for log in logs:
                if len(log.get("topics", [])) >= 3:
                    token0 = "0x" + log["topics"][1][-40:]
                    token1 = "0x" + log["topics"][2][-40:]
                    for token in [token0, token1]:
                        if token.lower() == WETH.lower() or token.lower() == WIF_TOKEN.lower():
                            continue
                        is_contract = await eth_get_code(token)
                        if is_contract:
                            from rpc import get_token_name, get_token_symbol
                            name = await get_token_name(token)
                            symbol = await get_token_symbol(token)
                            print(f"Scanner: new pool detected, {name} ({symbol}) {token}")
                            if _push_token({"address": token, "name": name, "symbol": symbol}):
                                found.append(token)
            LAST_BLOCK = current
    except Exception as e:
        print(f"Scanner error: {e}")
    return found

async def scan_loop():
    global LAST_BLOCK
    print("Scanner starting (Robinhood Chain - DexScreener + Uniswap V3 pools)...")
    LAST_BLOCK = await get_latest_block()
    print(f"Starting from block {LAST_BLOCK}")
    while True:
        await scan_once()
        await asyncio.sleep(30)
