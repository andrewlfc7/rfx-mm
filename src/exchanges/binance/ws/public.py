import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class WsStreamLinks:
    FUTURES_PUBLIC_STREAM: str = "wss://fstream.binance.com"
    SPOT_PUBLIC_STREAM = "wss://stream.binance.com:9443"


class BinancePublicWs:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.futures_base_url = WsStreamLinks.FUTURES_PUBLIC_STREAM
        self.spot_base_url = WsStreamLinks.SPOT_PUBLIC_STREAM


    def multi_stream_request(self, topics: List[str], **kwargs) -> Tuple[str, List[str]]:
        list_of_topics = []
        url = self.spot_base_url + "/stream?streams="

        for topic in topics:
            stream = ""
            if topic == "Trades":
                stream = f"{self.symbol.lower()}@trade/"
            elif topic == "Orderbook":
                stream = f"{self.symbol.lower()}@depth@100ms/"
            elif topic == "BBA":
                stream = f"{self.symbol.lower()}@bookTicker/"
            elif topic == "MarkPrice":
                stream = f"{self.symbol.lower()}@markPrice@1s/"
            elif topic == "Kline" and "interval" in kwargs:
                stream = f"{self.symbol.lower()}@kline_{kwargs['interval']}/"

            if stream:
                url += stream
                list_of_topics.append(stream[:-1])

        return url[:-1], list_of_topics


