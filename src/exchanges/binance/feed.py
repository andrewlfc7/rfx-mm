import asyncio
from typing import Tuple, Dict, List, Any
import ssl
import websockets
import orjson
from exchanges.binance.ws.handlers.trades import BinanceTradesHandler
from exchanges.binance.ws.handlers.kline import BinanceOhlcvHandler
from exchanges.binance.ws.handlers.orderbook import BinanceOrderbookHandler

from exchanges.binance.get.client import BinanceClient
from exchanges.binance.ws.public import BinancePublicWs


class BinanceWebsocket:
    """
    Handles Websocket connections and data management for Binance.
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.client = BinanceClient()
        self.ws_url, self.ws_topics = BinancePublicWs(self.symbol).multi_stream_request(
            topics=["Trades", "Orderbook", "Kline"], interval="1m"
        )
        self.data = {
            "orderbook": {},
            "trades": [],
            "ohlcv": []
        }

    def create_handlers(self) -> None:
        self.public_handler_map = {
            "depthUpdate": BinanceOrderbookHandler(size=100),
            "trade": BinanceTradesHandler(length=1000),
            "kline": BinanceOhlcvHandler(length=1000),
        }
        self.public_handler_map["bookTicker"] = self.public_handler_map["depthUpdate"]

    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        while True:
            try:
                orderbook_data = await self.client.get_order_book(self.symbol)
                self.public_handler_map["depthUpdate"].refresh(orderbook_data)
                await asyncio.sleep(timer)

            except Exception as e:
                print(f"Orderbook refresh error: {e}")

    async def refresh_trades_data(self, timer: int = 600) -> None:
        while True:
            try:
                trades_data = await self.client.get_recent_trades(self.symbol)
                self.public_handler_map["trade"].refresh(trades_data)
                await asyncio.sleep(timer)

            except Exception as e:
                print(f"Trades refresh error: {e}")

    async def refresh_ohlcv_data(self, timer: int = 600) -> None:
        while True:
            try:
                ohlcv_data = await self.client.get_klines(self.symbol, "1m")
                self.public_handler_map["kline"].refresh(ohlcv_data)
                await asyncio.sleep(timer)

            except Exception as e:
                print(f"OHLCV refresh error: {e}")

    def public_stream_sub(self) -> Tuple[str, Dict[str, Any]]:
        request = {
            "method": "SUBSCRIBE",
            "params": [
                f"{self.symbol.lower()}@trade",
                f"{self.symbol.lower()}@depth@100ms",
                f"{self.symbol.lower()}@kline_1m"
            ],
        }
        return (self.ws_url, request)


    async def public_stream_handler(self, recv: Dict[str, Any]) -> None:
        try:
            self.public_handler_map[recv["e"]].process(recv)
    
        except KeyError as ke:
            if "id" not in recv:
                raise ke
    
        except Exception as e:
            raise e

    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        try:
            url, requests = self.public_stream_sub()
            await self.start_public_ws(url, requests)
        except Exception as e:
            print(f"Public stream error: {e}")

    async def start_public_ws(self, url: str, request: List[Dict[str, Any]]) -> None:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with websockets.connect(url, ssl=ssl_context) as websocket:
            print(f"Connected to {url}")
            await websocket.send(orjson.dumps(request))
            try:
                while True:
                    recv = await websocket.recv()
                    data = orjson.loads(recv)
            except websockets.ConnectionClosed:
                print("Connection closed, reconnecting...")
                await self.start_public_ws(url, request)
            except Exception as e:
                print(f"Error with public websocket: {e}")

    async def start(self) -> None:
        self.create_handlers()
        await asyncio.gather(
            self.refresh_orderbook_data(),
            self.refresh_trades_data(),
            self.refresh_ohlcv_data(),
            self.start_public_stream(),
        )

    def get_latest_data(self):
        print("Fetching latest market data...") 
        
        orderbook_data = self.public_handler_map["depthUpdate"].recordable()
        trades_data = self.public_handler_map["trade"].recordable() 
        ohlcv_data = self.public_handler_map["kline"].recordable() 

        return {
            "orderbook": orderbook_data,
            "trades": trades_data,
            "ohlcv": ohlcv_data,
        }
