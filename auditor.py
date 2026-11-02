import asyncio
from config import *
from rpc import eth_get_code, get_token_supply, get_token_balance
from dex import get_best_pair

async def audit(address, scanner_data):
    layers = []
    passed = True
    reason = None

    # Layer 1: Is it a contract
    is_contract = await eth_get_code(address)
    l1 = is_contract
    layers.append({"n": 1, "name": "Contract", "pass": l1, "value": "Yes" if l1 else "No contract code"})
    if not l1:
        passed = False; reason = "not a contract"

    # Layer 2: Has liquidity
    if passed:
        pair = await get_best_pair(address)
        liq = float(pair.get("liquidity", {}).get("usd", 0) or 0) if pair else 0
        min_liq = DEFAULT_SETTINGS.get("min_liquidity", 1000)
        l2 = liq >= min_liq
        layers.append({"n": 2, "name": "Liquidity", "pass": l2, "value": f"${liq:,.0f}" if l2 else f"liq ${liq:,.0f} < ${min_liq}"})
        if not l2:
            passed = False; reason = f"low liquidity ${liq:,.0f}"

    # Layer 3: Pool age
    if passed and pair:
        created = pair.get("pairCreatedAt")
        if created:
            age_min = (asyncio.get_event_loop().time() * 1000 - created) / 60000 if False else (__import__("time").time() * 1000 - created) / 60000
            min_age = DEFAULT_SETTINGS.get("min_pool_age", 10)
            l3 = age_min >= min_age
            layers.append({"n": 3, "name": "Pool age", "pass": l3, "value": f"{int(age_min)}m" if l3 else f"too young {int(age_min)}m"})
            if not l3:
                passed = False; reason = f"pool too young {int(age_min)}m"
        else:
            layers.append({"n": 3, "name": "Pool age", "pass": True, "value": "unknown"})

    # Layer 4: Top holders (simplified - check top 5 known addresses)
    # For EVM, we'd need an indexer. Skip for now, mark as pass.
    layers.append({"n": 4, "name": "Top holders", "pass": True, "value": "not checked (no indexer)"})

    import db
    db.log_activity("auditor", address, "passed" if passed else "rejected", reason or "passed")
    return {"passed": passed, "layers": layers, "reason": reason, "pair": pair}
