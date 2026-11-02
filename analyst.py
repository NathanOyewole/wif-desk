import asyncio, httpx, json, time, re
from config import *
import db

async def fetch_dex_pair(address):
    from dex import get_best_pair
    return await get_best_pair(address)

async def score_rules(address, scanner_data, auditor_data):
    pair = auditor_data.get("pair") or scanner_data.get("pair")
    if not pair:
        return {"passed": False, "score": 0, "failed": ["no pair data"], "model": "rules", "inputTokens": 0,
                "answers": {"alive_6h": 0, "organic": 0, "flush": 0, "chase": 0}}

    liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
    vol_h1 = float(pair.get("volume", {}).get("h1", 0) or 0)
    pc_m5 = float(pair.get("priceChange", {}).get("m5", 0) or 0)
    pc_h1 = float(pair.get("priceChange", {}).get("h1", 0) or 0)
    buys_h1 = int(pair.get("txns", {}).get("h1", {}).get("buys", 0) or 0)
    buys_m5 = int(pair.get("txns", {}).get("m5", {}).get("buys", 0) or 0)
    sells_m5 = int(pair.get("txns", {}).get("m5", {}).get("sells", 0) or 0)

    alive_6h = min(vol_h1 / 25000, 1.0)
    organic = min(buys_h1 / 150, 1.0)
    if pc_m5 <= -5 and buys_m5 >= sells_m5:
        flush = 1.0
    elif pc_m5 < 0:
        flush = 0.5
    else:
        flush = 0.0
    chase = min(pc_h1 / 80, 1.0)

    score = round(100 * (alive_6h + organic + flush + (1 - chase)) / 4)
    failed = []
    if alive_6h < 0.70: failed.append(f"alive_6h {alive_6h:.2f}")
    if organic < 0.65: failed.append(f"organic {organic:.2f}")
    if chase > 0.30: failed.append(f"chase {chase:.2f}")
    if score < 70: failed.append(f"score {score}")

    result = {"answers": {"alive_6h": round(alive_6h, 2), "organic": round(organic, 2),
                          "flush": round(flush, 2), "chase": round(chase, 2)},
              "score": score, "passed": len(failed) == 0, "failed": failed,
              "model": "rules", "inputTokens": 0}
    db.log_activity("analyst", address, "passed" if result["passed"] else "rejected",
                    f"score {score}" + (f" ({', '.join(failed)})" if failed else ""))
    return result

async def analyze(address, scanner_data, auditor_data):
    return await score_rules(address, scanner_data, auditor_data)
