import aiohttp
import asyncio
import orjson
import logging


logger = logging.getLogger(__name__)


class BinanceClient:
    def __init__(self, base_url="https://api.binance.com"):
        self.base_url = base_url

    async def fetch(self, session, endpoint, params):
        """Fetch data from API endpoint using orjson"""
        try:
            url = f"{self.base_url}{endpoint}"
            async with session.get(url, params=params, ssl=False) as response:
                if response.status != 200:
                    logger.error(f"API error: {response.status} for {url}")
                    return None
                    
                data = await response.read() 
                return orjson.loads(data) 
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {endpoint}: {e}")
            return None
            
        except orjson.JSONDecodeError as e:
            logger.error(f"JSON decode error for {endpoint}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error fetching {endpoint}: {e}")
            return None

    async def get_order_book(self, symbol, limit=100):
        endpoint = "/api/v3/depth"
        params = {
            "symbol": symbol.upper(),
            "limit": limit
        }
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            return await self.fetch(session, endpoint, params)

    async def get_recent_trades(self, symbol, limit=500):
        endpoint = "/api/v3/trades"
        params = {
            "symbol": symbol.upper(),
            "limit": limit
        }
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            return await self.fetch(session, endpoint, params)

    async def get_klines(self, symbol, interval, limit=500, start_time=None, end_time=None):
        endpoint = "/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            return await self.fetch(session, endpoint, params)


