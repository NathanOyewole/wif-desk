import asyncio, time
from config import *
import db

async def risk_loop():
    print("Risk: monitoring positions")
    while True:
        await asyncio.sleep(15)
