import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from config import *
from db import init_db
import scanner, auditor, analyst, executor, risk, bus as bus_mod, telegram

async def pipeline():
    while True:
        coin = await bus_mod.bus.scanner_to_auditor.get()
        address = coin.get("mint")
        name = coin.get("name", "Unknown")
        try:
            audit_result = await auditor.audit(address, coin)
            if not audit_result["passed"]:
                continue
            analyst_result = await analyst.analyze(address, coin, audit_result)
            if not analyst_result["passed"]:
                continue
            await executor.execute(address, name, analyst_result, coin)
        except Exception as e:
            print(f"Pipeline error for {address}: {e}")

async def main():
    init_db()
    print("WIF Desk initialized. Starting agents...")
    await asyncio.gather(
        scanner.scan_loop(),
        risk.risk_loop(),
        pipeline(),
        telegram.poll_telegram(),
    )

if __name__ == "__main__":
    asyncio.run(main())
