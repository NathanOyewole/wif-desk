"""$wif token burn utility for Robinhood Chain."""
from config import *
from rpc import eth_call

# ERC-20 transfer function selector
TRANSFER_SELECTOR = "0xa9059cbb"

async def burn_wif(amount_wei, private_key=None):
    """
    Burn $wif by transferring to burn address.
    In PAPER mode, just log the burn.
    In LIVE mode, would sign and send tx.
    """
    print(f"[WIF BURN] Burning {amount_wei} wei to {WIF_BURN_ADDRESS}")
    return {"status": "burned", "amount": amount_wei, "to": WIF_BURN_ADDRESS}

async def get_wif_balance(address):
    """Get $wif balance for an address."""
    data = "0x70a08231" + address[2:].lower().zfill(64)
    result = await eth_call(WIF_TOKEN, data)
    if result and result != "0x":
        return int(result, 16)
    return 0
