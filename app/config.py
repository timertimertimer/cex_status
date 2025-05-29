import json
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.logger import logger


def find_project_root(file_name: str = '.env') -> Path:
    try:
        main_path = Path(sys.modules["__main__"].__file__).resolve()
        candidate = main_path.parent
        if (candidate / file_name).exists():
            return candidate
        if (candidate.parent / file_name).exists():
            return candidate.parent
    except Exception:
        pass
    return Path.cwd()


PROJECT_ROOT = find_project_root()
env_path = PROJECT_ROOT / ".env"
api_keys_path = PROJECT_ROOT / "api_keys.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=env_path, env_file_encoding="utf-8", extra="allow")

    seconds_in_one_minute: int = 60
    cex_data_update_ttl_minutes: int = 5
    dv_currencies_update_ttl_minutes: int = 30

    merchant_host: str
    store_api_key: str
    cex_data_ttl: int = seconds_in_one_minute * cex_data_update_ttl_minutes
    dv_currencies_ttl: int = seconds_in_one_minute * dv_currencies_update_ttl_minutes


settings = Settings()
logger.info(settings)
dv_network_map = {
    'bitcoin': ['BTC', 'BRC20'],
    'ethereum': ['ETH', 'ERC20'],
    'tron': ['TRX', 'TRC20', 'TRX1'],
    'litecoin': ['LTC'],
    'bitcoincash': ['BCH', 'bchn'],
    'bsc': ['BSC', 'BEP20'],
    'polygon': ['MATIC', 'POLYGON'],
    # 'ton': ['TON']
}
exchanges = [
    'htx', 'okx', 'binance', 'bitget', 'kucoin',
    'mexc'  # no deposit limits
]

with open(api_keys_path, encoding='utf-8') as file:
    api_keys = json.load(file)
