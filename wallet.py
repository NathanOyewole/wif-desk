import os
from web3 import Web3
from eth_account import Account
from config import RH_RPC_URL

_w3 = Web3(Web3.HTTPProvider(RH_RPC_URL))
_key = os.getenv("WALLET_PRIVATE_KEY", "").strip()
_account = Account.from_key(_key) if _key else None

def is_configured():
    return _account is not None

def address():
    return _account.address if _account else None

def balance_wei():
    if not _account:
        return 0
    return _w3.eth.get_balance(_account.address)

def balance_eth():
    return _w3.from_wei(balance_wei(), "ether") if _account else 0

def nonce():
    return _w3.eth.get_transaction_count(_account.address) if _account else 0

def send_tx(tx):
    if not _account:
        raise RuntimeError("Wallet not configured")
    signed = _account.sign_transaction(tx)
    return _w3.eth.send_raw_transaction(signed.rawTransaction)

def wait_receipt(tx_hash, timeout=60):
    return _w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

def estimate_gas(tx):
    return _w3.eth.estimate_gas(tx)
