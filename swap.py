from web3 import Web3
from config import RH_RPC_URL, WETH, UNI_SWAP_ROUTER
import wallet

_w3 = Web3(Web3.HTTPProvider(RH_RPC_URL))

WETH = Web3.to_checksum_address(WETH)
ROUTER = Web3.to_checksum_address(UNI_SWAP_ROUTER)

WETH_ABI = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name": "wad", "type": "uint256"}], "name": "withdraw", "outputs": [], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
]

ROUTER_ABI = [
    {"constant": False, "inputs": [{"name": "params", "type": "tuple", "components": [
        {"name": "tokenIn", "type": "address"},
        {"name": "tokenOut", "type": "address"},
        {"name": "fee", "type": "uint24"},
        {"name": "recipient", "type": "address"},
        {"name": "deadline", "type": "uint256"},
        {"name": "amountIn", "type": "uint256"},
        {"name": "amountOutMinimum", "type": "uint256"},
        {"name": "sqrtPriceLimitX96", "type": "uint160"},
    ]}], "name": "exactInputSingle", "outputs": [{"name": "amountOut", "type": "uint256"}], "payable": True, "stateMutability": "payable", "type": "function"},
]

_weth = _w3.eth.contract(address=WETH, abi=WETH_ABI)
_router = _w3.eth.contract(address=ROUTER, abi=ROUTER_ABI)

FEES = [500, 3000, 10000]

def find_pool(token_address):
    """Find a v3 pool for token/WETH and return (pool_address, fee)."""
    token = Web3.to_checksum_address(token_address)
    factory = Web3.to_checksum_address("0x1f7d7550b1b028f7571e69a784071f0205fd2efa")
    sel = _w3.keccak(text="getPool(address,address,uint24)")[:4].hex()
    for fee in FEES:
        data = sel + "0" * 24 + token[2:].lower() + "0" * 24 + WETH[2:].lower() + hex(fee)[2:].zfill(64)
        try:
            res = _w3.eth.call({"to": factory, "data": data})
            pool = Web3.to_checksum_address("0x" + res.hex()[-40:])
            if pool != "0x0000000000000000000000000000000000000000" and len(_w3.eth.get_code(pool)) > 0:
                return pool, fee
        except Exception:
            continue
    return None, None

def _approve(token, spender, amount):
    if token.lower() == WETH.lower():
        contract = _weth
    else:
        contract = _w3.eth.contract(address=Web3.to_checksum_address(token), abi=WETH_ABI)
    tx = contract.functions.approve(spender, amount).build_transaction({
        "from": wallet.address(), "nonce": wallet.nonce(), "gas": 100000, "gasPrice": _w3.eth.gas_price,
    })
    return wallet.send_tx(tx)

def wrap_eth(amount_wei):
    tx = _weth.functions.deposit().build_transaction({
        "from": wallet.address(), "value": amount_wei, "nonce": wallet.nonce(),
        "gas": 100000, "gasPrice": _w3.eth.gas_price,
    })
    return wallet.send_tx(tx)

def unwrap_eth(amount_wei):
    tx = _weth.functions.withdraw(amount_wei).build_transaction({
        "from": wallet.address(), "nonce": wallet.nonce(), "gas": 100000, "gasPrice": _w3.eth.gas_price,
    })
    return wallet.send_tx(tx)

def swap_eth_for_token(token_address, amount_in_wei, slippage_pct=1.0):
    """Buy token with native ETH. Returns (tx_hash, pool, fee)."""
    if not wallet.is_configured():
        raise RuntimeError("Wallet not configured")
    token = Web3.to_checksum_address(token_address)
    pool, fee = find_pool(token)
    if not pool:
        raise RuntimeError("No v3 pool found for token/WETH")
    # 1. wrap ETH
    wrap_eth(amount_in_wei)
    # 2. approve router
    _approve(WETH, ROUTER, amount_in_wei)
    # 3. swap
    import time
    params = (WETH, token, fee, wallet.address(), int(time.time()) + 600,
              amount_in_wei, 0, 0)
    tx = _router.functions.exactInputSingle(params).build_transaction({
        "from": wallet.address(), "value": 0, "nonce": wallet.nonce(),
        "gas": 300000, "gasPrice": _w3.eth.gas_price,
    })
    return wallet.send_tx(tx), pool, fee

def swap_token_for_eth(token_address, amount_in_wei, slippage_pct=1.0):
    """Sell token for native ETH. Returns (tx_hash, pool, fee)."""
    if not wallet.is_configured():
        raise RuntimeError("Wallet not configured")
    token = Web3.to_checksum_address(token_address)
    pool, fee = find_pool(token)
    if not pool:
        raise RuntimeError("No v3 pool found for token/WETH")
    _approve(token, ROUTER, amount_in_wei)
    import time
    params = (token, WETH, fee, wallet.address(), int(time.time()) + 600,
              amount_in_wei, 0, 0)
    tx = _router.functions.exactInputSingle(params).build_transaction({
        "from": wallet.address(), "value": 0, "nonce": wallet.nonce(),
        "gas": 300000, "gasPrice": _w3.eth.gas_price,
    })
    h = wallet.send_tx(tx)
    unwrap_eth(amount_in_wei)
    return h, pool, fee

WIF_ADDRESS = "0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B"
DEAD_ADDRESS = "0x000000000000000000000000000000000000dEaD"

ERC20_ABI = [
    {"constant": False, "inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "payable": False, "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "payable": False, "stateMutability": "view", "type": "function"},
]

def wif_decimals():
    token = _w3.eth.contract(address=Web3.to_checksum_address(WIF_ADDRESS), abi=ERC20_ABI)
    return token.functions.decimals().call()

def wif_balance():
    if not wallet.is_configured():
        return 0
    token = _w3.eth.contract(address=Web3.to_checksum_address(WIF_ADDRESS), abi=ERC20_ABI)
    return token.functions.balanceOf(wallet.address()).call()

def burn_wif(amount_wei):
    """Send $wif to the dead address (permanent burn). Returns tx hash."""
    if not wallet.is_configured():
        raise RuntimeError("Wallet not configured")
    token = _w3.eth.contract(address=Web3.to_checksum_address(WIF_ADDRESS), abi=ERC20_ABI)
    tx = token.functions.transfer(Web3.to_checksum_address(DEAD_ADDRESS), amount_wei).build_transaction({
        "from": wallet.address(), "nonce": wallet.nonce(), "gas": 100000, "gasPrice": _w3.eth.gas_price,
    })
    return wallet.send_tx(tx)
