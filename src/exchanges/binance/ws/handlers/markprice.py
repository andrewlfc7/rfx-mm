from typing import Dict

class Ticker:
    def __init__(self, fundingTime: float = None, fundingRate: float = None, markPrice: float = None, indexPrice: float = None):
        self._fundingTime = fundingTime
        self._fundingRate = fundingRate
        self._markPrice = markPrice
        self._indexPrice = indexPrice

    @property
    def fundingTime(self):
        return self._fundingTime

    @property
    def fundingRate(self):
        return self._fundingRate

    @property
    def markPrice(self):
        return self._markPrice

    @property
    def indexPrice(self):
        return self._indexPrice

    @property
    def fundingRateBps(self):
        return self._fundingRate * 10_000.0

    def reset(self):
        self._fundingTime = None
        self._fundingRate = None
        self._markPrice = None
        self._indexPrice = None

    def recordable(self):
        return {
            "fundingTime": self.fundingTime,
            "fundingRate": self.fundingRate,
            "markPrice": self.markPrice,
            "indexPrice": self.indexPrice,
        }

    def update(self, fundingTime: float = None, fundingRate: float = None, markPrice: float = None, indexPrice: float = None):
        if fundingTime is not None:
            self._fundingTime = fundingTime
        if fundingRate is not None:
            self._fundingRate = fundingRate
        if markPrice is not None:
            self._markPrice = markPrice
        if indexPrice is not None:
            self._indexPrice = indexPrice

class BinanceTickerHandler(Ticker):
    def __init__(self, fundingTime: float = None, fundingRate: float = None, markPrice: float = None, indexPrice: float = None):
        super().__init__(fundingTime, fundingRate, markPrice, indexPrice)

    def refresh(self, recv: Dict):
        try:
            self.update(
                fundingTime=float(recv.get("lastFundingTime", self.fundingTime)),
                fundingRate=float(recv.get("fundingRate", self.fundingRate)),
                markPrice=float(recv.get("markPrice", self.markPrice)),
                indexPrice=float(recv.get("indexPrice", self.indexPrice)),
            )
        except Exception as e:
            raise Exception(f"Ticker refresh - {e}")

    def process(self, recv: Dict):
        try:
            self.update(
                fundingTime=float(recv.get("T", self.fundingTime)),
                fundingRate=float(recv.get("r", self.fundingRate)),
                markPrice=float(recv.get("p", self.markPrice)),
                indexPrice=float(recv.get("i", self.indexPrice)),
            )
        except Exception as e:
            raise Exception(f"Ticker process - {e}")
