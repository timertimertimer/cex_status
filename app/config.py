import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='../.env', env_file_encoding="utf-8", extra="allow")

    seconds_in_one_minute: int = 60
    cex_data_update_ttl_minutes: int = 5
    dv_currencies_update_ttl_minutes: int = 30

    merchant_host: str
    store_api_key: str
    cex_data_ttl: int = seconds_in_one_minute * cex_data_update_ttl_minutes
    dv_currencies_ttl: int = seconds_in_one_minute * dv_currencies_update_ttl_minutes


settings = Settings()
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

with open('../api_keys.json', encoding='utf-8') as file:
    api_keys = json.load(file)
