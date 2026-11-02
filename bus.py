import asyncio
class Bus:
    def __init__(self):
        self.scanner_to_auditor = asyncio.Queue()
        self.auditor_to_analyst = asyncio.Queue()
        self.analyst_to_executor = asyncio.Queue()
bus = Bus()
