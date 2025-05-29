import asyncio
import json
import time
from pathlib import Path
from typing import Dict

import ccxt.async_support as ccxt
from ccxt.base.exchange import Exchange
import redis.asyncio as redis

from app.config import settings, api_keys, dv_network_map, exchanges
from app.dv_api import DVAPI
from app.logger import logger



redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

dv_api = DVAPI()
dv_currencies_path = Path("dv_currencies.json")
dv_cache_key = "dv:currencies"

async def load_dv_currencies():
    cached = await redis_client.get(dv_cache_key)
    if cached:
        return json.loads(cached)
    return None


async def update_dv_currencies():
    cached = await load_dv_currencies()
    if cached:
        return cached
    logger.info(f"Updating DV currencies data")
    currencies = await dv_api.get_store_currencies()
    await redis_client.set(dv_cache_key, json.dumps(currencies), ex=settings.cex_data_ttl)
    return currencies


async def get_cex_data(exchange: str, dv_network: str, dv_coin: str):
    exc_obj = getattr(ccxt, exchange)(
        {
            "apiKey": api_keys[exchange]["api_key"],
            "secret": api_keys[exchange]["secret_key"],
            "password": api_keys[exchange].get("passphrase"),
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 10_000
            },
            'commonCurrencies': {'XBT': 'XBT', 'BTC': 'BTC'} if exchange == 'mexc' else Exchange.commonCurrencies,
        } if api_keys.get(exchange) else {}
    )

    try:
        data = await exc_obj.fetch_currencies()
    except Exception as e:
        logger.error(type(e), e)
        await exc_obj.close()
        return None

    coin_data = None
    try:
        for net in dv_network_map.get(dv_network, []):
            coin_data = data.get(dv_coin, {}).get("networks", {}).get(net)
            if coin_data:
                break
    except KeyError as e:
        logger.error(e)
        await exc_obj.close()
        return None

    await exc_obj.close()
    if not coin_data:
        return {"network": dv_network, "can_deposit": False}

    return {
        "network": net,
        "can_deposit": coin_data.get("deposit", False),
        "limits": coin_data.get("limits", {}).get("deposit"),
    }


async def update_cex_data():
    logger.info(f"Updating cex data")
    dv_currencies = await update_dv_currencies()
    result: Dict[str, Dict] = {}

    async def fetch_exchange_currencies(exchange: str):
        exc_obj = getattr(ccxt, exchange)(
            {
                "apiKey": api_keys[exchange]["api_key"],
                "secret": api_keys[exchange]["secret_key"],
                "password": api_keys[exchange].get("passphrase"),
                'options': {
                    'adjustForTimeDifference': True,
                },
                'commonCurrencies': {'XBT': 'XBT', 'BTC': 'BTC'}
                if exchange == 'mexc' else Exchange.commonCurrencies,
            } if api_keys.get(exchange) else {}
        )
        try:
            data = await exc_obj.fetch_currencies()
            logger.info(f"[{exchange}] fetch_currencies returned {len(data)} currencies")
        except Exception as e:
            logger.info(f"[{exchange}] fetch_currencies failed:", type(e), e)
            data = {}
        if not data:
            logger.info(f"[{exchange}] fetch_currencies return None")
        await exc_obj.close()
        return exchange, data

    exchange_currency_data = {exchange: data for exchange, data in await asyncio.gather(
        *(fetch_exchange_currencies(exchange) for exchange in exchanges)
    )}

    for token_obj in dv_currencies:
        dv_coin = token_obj['code']
        dv_network = token_obj['blockchain']
        token_result = {dv_network: {}}

        for exchange in exchanges:
            data = exchange_currency_data.get(exchange, {})
            coin_data = None
            network_used = None
            try:
                for net in dv_network_map.get(dv_network, []):
                    coin_data = data.get(dv_coin, {}).get("networks", {}).get(net)
                    if coin_data:
                        network_used = net
                        break
            except KeyError as e:
                logger.error(f"[{exchange}] Error processing {dv_coin}: {e}")
                continue

            if coin_data:
                token_result[dv_network][exchange] = {
                    "network": network_used,
                    "deposit": coin_data.get("deposit", False),
                    "withdraw": coin_data.get("withdraw", False),
                    "limits": coin_data.get("limits"),
                    # "fee": coin_data.get("fee")
                }
            else:
                token_result[dv_network][exchange] = {
                    "network": None,
                    "deposit": False,
                    "withdraw": False,
                    "limits": None,
                    # "fee": None
                }

        if dv_coin in result:
            result[dv_coin].update(token_result)
        else:
            result[dv_coin] = token_result
        await redis_client.set(f"cex:token:{dv_coin}", json.dumps(result[dv_coin]), ex=settings.cex_data_ttl)

    await redis_client.set("cex:full_data", json.dumps(result), ex=settings.cex_data_ttl)


async def get_full_data():
    raw = await redis_client.get("cex:full_data")
    if raw:
        return json.loads(raw)
    return None


async def get_token_data_from_cache(token: str):
    raw = await redis_client.get(f"cex:token:{token}")
    if raw:
        return json.loads(raw)
    return None


if __name__ == '__main__':
    start = time.time()
    asyncio.run(update_cex_data())
    end = time.time()
    print(f'Total time: {end - start} seconds')
