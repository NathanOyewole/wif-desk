import asyncio, httpx, json, time, re
from config import *
import db

async def fetch_dex_pair(address):
    from dex import get_best_pair
    return get_best_pair(address)

async def score_rules(address, scanner_data, auditor_data):
    pair = auditor_data.get("pair") or scanner_data.get("pair")
    if not pair:
        return {"passed": False, "score": 0, "failed": ["no pair data"], "model": "rules", "inputTokens": 0,
                "answers": {"alive": 0, "organic": 0, "flush": 0, "chase": 0}}

    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
    vol_h24 = float(pair.get("volume", {}).get("h24", 0) or 0)
    pc_h6 = float(pair.get("priceChange", {}).get("h6", 0) or 0)
    pc_h24 = float(pair.get("priceChange", {}).get("h24", 0) or 0)
    buys_h24 = int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0)
    sells_h24 = int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0)

    alive = min(vol_h24 / 50000, 1.0)
    organic = min(max(buys_h24 - sells_h24, 0) / 200, 1.0)
    if pc_h6 <= -5 and buys_h24 >= sells_h24:
        flush = 1.0
    elif pc_h6 < 0:
        flush = 0.5
    else:
        flush = 0.0
    chase = min(max(pc_h24, 0) / 80, 1.0)

    score = round(100 * (alive + organic + flush + (1 - chase)) / 4)
    failed = []
    if alive < 0.30: failed.append(f"alive {alive:.2f}")
    if organic < 0.15: failed.append(f"organic {organic:.2f}")
    if chase > 0.50: failed.append(f"chase {chase:.2f}")
    if score < 40: failed.append(f"score {score}")

    result = {"answers": {"alive": round(alive, 2), "organic": round(organic, 2),
                          "flush": round(flush, 2), "chase": round(chase, 2)},
              "score": score, "passed": len(failed) == 0, "failed": failed,
              "model": "rules", "inputTokens": 0}
    db.log_activity("analyst", address, "passed" if result["passed"] else "rejected",
                    f"score {score}" + (f" ({', '.join(failed)})" if failed else ""))
    return result

async def analyze(address, scanner_data, auditor_data):
    return await score_rules(address, scanner_data, auditor_data)
