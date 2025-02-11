from typing import List, Dict, Any
import numpy as np
from dataclasses import dataclass
from numpy_ringbuffer import RingBuffer

@dataclass
class Trade:
    timestamp: float
    side: float
    price: float
    size: float

    @staticmethod
    def from_array(arr):
        return Trade(
            timestamp=arr[0],
            side=arr[1],
            price=arr[2],
            size=arr[3]
        )

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "side": self.side,
            "price": self.price,
            "size": self.size
        }

class Trades:
    def __init__(self, length: int = 1000):
        self.length = length
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 4))

    def reset(self):
        self._rb_ = RingBuffer(self.length, dtype=(np.float64, 4))

    def recordable(self):
        return [Trade.from_array(trade).to_dict() for trade in self._rb_]

    def add_single(self, trade: Trade):
        self._rb_.append(np.array([trade.timestamp, trade.side, trade.price, trade.size], dtype=np.float64))

    def add_many(self, trades: List[Trade]):
        for trade in trades:
            self.add_single(trade)

    def unwrap(self):
        return self._rb_._unwrap()

    def __eq__(self, other):
        if isinstance(other, Trades):
            return np.array_equal(self.unwrap(), other.unwrap())
        return False

    def __getitem__(self, idx):
        return self.unwrap()[idx]

    def __len__(self):
        return len(self._rb_)

    def __repr__(self):
        return f"Trades(length={self.length}, trades={self.unwrap()})"

class Side:
    BUY = 1.0
    SELL = -1.0

class BinanceTradesHandler(Trades):
    def __init__(self, length: int = 1000):
        super().__init__(length)

    def refresh(self, recv: List[Dict]):
        try:
            self.reset()
            new_trades = [Trade(
                timestamp=float(trade.get("time")),
                side=Side.SELL if trade.get("isBuyerMaker") else Side.BUY,
                price=float(trade.get("price")),
                size=float(trade.get("qty"))
            ) for trade in recv]
            self.add_many(new_trades)
        except Exception as e:
            raise Exception(f"Trades refresh - {e}")

    def process(self, recv: Dict[str, Any]):
        try:
            self.add_single(Trade(
                timestamp=float(recv.get("T")),
                side=Side.SELL if recv.get("m") else Side.BUY,
                price=float(recv.get("p")),
                size=float(recv.get("q"))
            ))
        except Exception as e:
            raise Exception(f"Trades process - {e}")
