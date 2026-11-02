import httpx, json

async def fetch_pairs(token_address):
    """Fetch DexScreener pairs for a token on Robinhood Chain."""
    async with httpx.AsyncClient(timeout=15, headers={"Host": "api.dexscreener.com"}) as client:
        r = await client.get(f"https://104.21.48.1/tokens/v1/robinhood/{token_address}")
        data = r.json() if r.status_code == 200 else []
        return data if isinstance(data, list) else []

async def fetch_token_profiles():
    """Fetch latest token profiles on Robinhood Chain."""
    async with httpx.AsyncClient(timeout=15, headers={"Host": "api.dexscreener.com"}) as client:
        r = await client.get("https://104.21.48.1/token-profiles/latest/v1")
        data = r.json() if r.status_code == 200 else []
        # Filter for robinhood chain
        return [p for p in data if p.get("chainId") == "robinhood"] if isinstance(data, list) else []

async def get_best_pair(token_address):
    """Get the best (most liquid) pair for a token."""
    pairs = await fetch_pairs(token_address)
    if not pairs:
        return None
    return max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
