import numpy as np
from numba.experimental import jitclass
from numba.types import uint32, int32, float64
from typing import Dict, Union

from numba import njit
from numba.types import Array, bool_

@njit(fastmath=True)
def nbisin(a: Array, b: Array) -> Array:
    out = np.empty(a.size, dtype=bool_)
    b = set(b)

    for i in range(a.size):
        out[i] = a[i] in b

    return out

# @jitclass
class Orderbook:
    size: uint32
    asks: float64[:, :]
    bids: float64[:, :]
    bba: float64[:, :]
    seq_id: int32

    def __init__(self, size: int):
        self.size = size
        self.asks = np.zeros((self.size, 2), dtype=np.float64)
        self.bids = np.zeros((self.size, 2), dtype=np.float64)
        self.bba = np.zeros((2, 2), dtype=np.float64)
        self.seq_id = 0

    def reset(self):
        self.asks.fill(0)
        self.bids.fill(0)
        self.bba.fill(0)
        self.seq_id = 0

    def recordable(self):
        return {
            "seq_id": np.float64(self.seq_id),
            "asks": self.asks.astype(np.float64),
            "bids": self.bids.astype(np.float64)
        }

    def sort_bids(self):
        self.bids = self.bids[self.bids[:, 0].argsort()][::-1][: self.size]
        self.bba[0, :] = self.bids[0]

    def sort_asks(self):
        self.asks = self.asks[self.asks[:, 0].argsort()][: self.size]
        self.bba[1, :] = self.asks[0]

    def refresh(self, asks, bids, new_seq_id: int):
        self.reset()
        self.seq_id = new_seq_id
        max_asks_idx = min(asks.shape[0], self.size)
        max_bids_idx = min(bids.shape[0], self.size)
        self.asks[:max_asks_idx, :] = asks[:max_asks_idx, :]
        self.bids[:max_bids_idx, :] = bids[:max_bids_idx, :]
        self.sort_bids()
        self.sort_asks()

    def update_bids(self, bids, new_seq_id: int):
        if bids.size == 0 or new_seq_id < self.seq_id:
            return
        self.seq_id = new_seq_id
        self.bids = self.bids[~nbisin(self.bids[:, 0], bids[:, 0])]
        self.bids = np.vstack((self.bids, bids[bids[:, 1] != 0]))
        self.sort_bids()

    def update_asks(self, asks, new_seq_id: int):
        if asks.size == 0 or new_seq_id < self.seq_id:
            return
        self.seq_id = new_seq_id
        self.asks = self.asks[~nbisin(self.asks[:, 0], asks[:, 0])]
        self.asks = np.vstack((self.asks, asks[asks[:, 1] != 0]))
        self.sort_asks()

    def update_full(self, asks, bids, new_seq_id: int):
        self.update_asks(asks, new_seq_id)
        self.update_bids(bids, new_seq_id)

class BinanceOrderbookHandler(Orderbook):
    def __init__(self, size: int):
        super().__init__(size)

    def refresh(self, recv: Dict):
        try:
            seq_id = int(recv.get("lastUpdateId"))
            bids = np.array(recv.get("bids"), dtype=np.float64)
            asks = np.array(recv.get("asks"), dtype=np.float64)
            # self.refresh(asks, bids, seq_id)
            super().refresh(asks, bids, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook refresh - {e}")

    def process(self, recv: Dict):
        try:
            seq_id = int(recv.get("u"))
            if recv.get("b", []):
                bids = np.array(recv["b"], dtype=np.float64)
                self.update_bids(bids, seq_id)
            if recv.get("a", []):
                asks = np.array(recv["a"], dtype=np.float64)
                self.update_asks(asks, seq_id)
        except Exception as e:
            raise Exception(f"Orderbook process - {e}")
