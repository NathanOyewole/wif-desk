import os as _os
_env_path = _os.path.join(_os.path.dirname(__file__), '.env')
if _os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                _os.environ.setdefault(_k, _v)
import os
RH_CHAIN_ID = 46630
RH_RPC_URL = os.getenv("RH_RPC_URL", "https://rpc.testnet.chain.robinhood.com")
WIF_TOKEN = "0xE49A1C3033EcC6b804bc423021D3F71F1A3e0F9B"
WIF_BURN_ADDRESS = "0x000000000000000000000000000000000000dead"
WETH = "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73"
UNI_V3_FACTORY = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
UNI_SWAP_ROUTER = "0xcaf681a66d020601342297493863e78c959e5cb2"
TG_TOKEN = os.getenv("TG_TOKEN", "")
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "0"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_SETTINGS = {"stack": 200.0, "mode": "PAPER", "min_liquidity": 1000, "min_pool_age": 10, "max_top10_pct": 25, "max_h1_change": 80, "stop_pct": 6, "trail_pct": 12, "trail_activate_pct": 20, "timeout_hours": 3, "executor_size_pct": 8, "min_trade_size": 10.0, "below_min_action": "bump", "analyst_mode": "rules"}
