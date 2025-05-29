import asyncio

import httpx

from app.config import settings

class DVAPI:
    def __init__(self, merchant_host: str = settings.merchant_host):
        self.client = httpx.AsyncClient(
            base_url=f'https://{merchant_host}',
            headers={"Content-Type": "application/json", "x-api-key": settings.store_api_key}
        )

    async def get_store_currencies(self) -> list[dict]:
        response = await self.client.get('/api/v1/external/store/currencies')
        data = response.json()
        return data['data']


if __name__ == '__main__':
    asyncio.run(DVAPI(settings.merchant_host).get_store_currencies())