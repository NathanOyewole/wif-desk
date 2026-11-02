import asyncio, time, json
from config import *
from rpc import eth_get_code
import db
import bus as bus_mod

# Uniswap V3 PoolCreated event signature
POOL_CREATED_TOPIC = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
LAST_BLOCK = 0

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

async def scan_loop():
    global LAST_BLOCK
    print("Scanner starting (Robinhood Chain - Uniswap V3 pools)...")
    LAST_BLOCK = await get_latest_block()
    print(f"Starting from block {LAST_BLOCK}")
    while True:
        try:
            current = await get_latest_block()
            if current > LAST_BLOCK:
                logs = await get_logs(LAST_BLOCK + 1, current)
                for log in logs:
                    # Parse PoolCreated event
                    # topics[1] = token0, topics[2] = token1, topics[3] = fee
                    if len(log.get("topics", [])) >= 3:
                        token0 = "0x" + log["topics"][1][-40:]
                        token1 = "0x" + log["topics"][2][-40:]
                        # One of these is likely a new token, the other is WETH or $wif
                        for token in [token0, token1]:
                            if token.lower() == WETH.lower() or token.lower() == WIF_TOKEN.lower():
                                continue
                            # Check if it's a contract
                            is_contract = await eth_get_code(token)
                            if is_contract:
                                from rpc import get_token_name, get_token_symbol
                                name = await get_token_name(token)
                                symbol = await get_token_symbol(token)
                                print(f"Scanner: new pool detected, {name} ({symbol}) {token}")
                                db.save_coin(token, name, symbol, 0, "0")
                                await bus_mod.bus.scanner_to_auditor.put({
                                    "mint": token, "name": name, "symbol": symbol,
                                    "liquidity_usd": 0, "price_usd": "0", "pair": None
                                })
                LAST_BLOCK = current
        except Exception as e:
            print(f"Scanner error: {e}")
        await asyncio.sleep(10)
