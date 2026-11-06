import subprocess, json

DEX_HOST = "api.dexscreener.com"
DEX_IP = "104.21.48.1"

def _fetch(url):
    """Fetch via curl with a pinned IP (sandbox DNS can't resolve the host)."""
    out = subprocess.run(
        ["curl", "-s", "-m", "15", "--resolve", f"{DEX_HOST}:443:{DEX_IP}", url],
        capture_output=True, text=True,
    )
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        return json.loads(out.stdout)
    except Exception:
        return None

def fetch_pairs(token_address):
    data = _fetch(f"https://{DEX_HOST}/tokens/v1/robinhood/{token_address}")
    return data if isinstance(data, list) else []

def fetch_token_profiles():
    data = _fetch(f"https://{DEX_HOST}/token-profiles/latest/v1")
    return [p for p in data if p.get("chainId") == "robinhood"] if isinstance(data, list) else []

def get_best_pair(token_address):
    pairs = fetch_pairs(token_address)
    if not pairs:
        return None
    return max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))

def search_tokens(chain="robinhood", limit=20):
    data = _fetch(f"https://{DEX_HOST}/latest/dex/search?q={chain}")
    pairs = data.get("pairs", []) if isinstance(data, dict) else []
    out = []
    for p in pairs:
        if p.get("chainId") != chain:
            continue
        base = p.get("baseToken", {})
        out.append({
            "address": base.get("address"),
            "name": base.get("name"),
            "symbol": base.get("symbol"),
            "priceUsd": p.get("priceUsd"),
            "liquidity_usd": float(p.get("liquidity", {}).get("usd", 0) or 0),
        })
    return out[:limit]
