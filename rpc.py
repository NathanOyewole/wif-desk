from config import *
import httpx, json

async def eth_call(to, data):
    """Make an eth_call to Robinhood Chain."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": to, "data": data}, "latest"]}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(RH_RPC_URL, json=payload)
        return r.json().get("result") if r.status_code == 200 else None

async def eth_get_code(address):
    """Check if address is a contract."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getCode", "params": [address, "latest"]}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(RH_RPC_URL, json=payload)
        result = r.json().get("result", "0x") if r.status_code == 200 else "0x"
        return result != "0x"

async def get_token_balance(token, owner):
    """ERC-20 balanceOf."""
    data = "0x70a08231" + owner[2:].lower().zfill(64)
    result = await eth_call(token, data)
    if result and result != "0x":
        return int(result, 16)
    return 0

async def get_token_supply(token):
    """ERC-20 totalSupply."""
    data = "0x18160ddd"
    result = await eth_call(token, data)
    if result and result != "0x":
        return int(result, 16)
    return 0

async def get_token_decimals(token):
    """ERC-20 decimals."""
    data = "0x313ce567"
    result = await eth_call(token, data)
    if result and result != "0x":
        return int(result, 16)
    return 18

async def get_token_name(token):
    """ERC-20 name()."""
    result = await eth_call(token, '0x06fdde03')
    if result and result != '0x':
        # Decode string
        try:
            hex_str = result[2:]
            # Skip first 64 chars (offset), next 64 (length)
            if len(hex_str) > 128:
                length = int(hex_str[64:128], 16)
                name_hex = hex_str[128:128 + length * 2]
                return bytes.fromhex(name_hex).decode('utf-8', errors='ignore').strip('')
        except:
            pass
    return 'Unknown'

async def get_token_symbol(token):
    """ERC-20 symbol()."""
    result = await eth_call(token, '0x95d89b41')
    if result and result != '0x':
        try:
            hex_str = result[2:]
            if len(hex_str) > 128:
                length = int(hex_str[64:128], 16)
                sym_hex = hex_str[128:128 + length * 2]
                return bytes.fromhex(sym_hex).decode('utf-8', errors='ignore').strip('')
            elif len(hex_str) <= 64:
                # bytes32
                return bytes.fromhex(hex_str).decode('utf-8', errors='ignore').strip('')
        except:
            pass
    return '???'
