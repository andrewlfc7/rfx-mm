from typing import List, Dict, Any
import numpy as np
from dataclasses import dataclass
from numpy_ringbuffer import RingBuffer

@dataclass
class OHLCV:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float

    @staticmethod
    def from_array(arr):
        return OHLCV(
            timestamp=arr[0],
            open=arr[1],
            high=arr[2],
            low=arr[3],
            close=arr[4],
            volume=arr[5]
        )

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }

class Candles:
    def __init__(self, length: int = 1000):
        self.length = length
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 6))
        self._latest_timestamp_ = 0

    def reset(self):
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 6))
        self._latest_timestamp_ = 0

    def add_single(self, candle: OHLCV):
        if candle.timestamp > self._latest_timestamp_:
            self._latest_timestamp_ = candle.timestamp
        else:
            self._rb_.pop()
        self._rb_.append(np.array([
            candle.timestamp, candle.open, candle.high, candle.low, candle.close, candle.volume
        ], dtype=np.float64))

    def add_many(self, candles: List[OHLCV]):
        for candle in candles:
            self.add_single(candle)

    def unwrap(self):
        return self._rb_._unwrap()

    def recordable(self):
        return [OHLCV.from_array(ohlcv).to_dict() for ohlcv in self._rb_]

    def __eq__(self, other):
        if isinstance(other, Candles):
            return np.array_equal(self.unwrap(), other.unwrap())
        return False

    def __len__(self):
        return self._rb_.__len__()

    def __getitem__(self, idx):
        return self.unwrap()[idx]

    def __repr__(self):
        return f"Candles(length={self.length}, candles={self.unwrap()})"

class BinanceOhlcvHandler(Candles):
    def __init__(self, length: int = 1000):
        super().__init__(length)

    def refresh(self, recv: List[List]):
        try:
            self.reset()
            new_candles = [OHLCV(
                timestamp=float(candle[0]),
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5])
            ) for candle in recv]
            self.add_many(new_candles)
        except Exception as e:
            raise Exception(f"OHLCV refresh - {e}")

    def process(self, recv: Dict[str, Any]):
        try:
            candle = recv["k"]
            self.add_single(OHLCV(
                timestamp=float(candle.get("t")),
                open=float(candle.get("o")),
                high=float(candle.get("h")),
                low=float(candle.get("l")),
                close=float(candle.get("c")),
                volume=float(candle.get("v"))
            ))
        except Exception as e:
            raise Exception(f"OHLCV process - {e}")
