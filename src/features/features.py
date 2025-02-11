import time
from typing import Dict, Optional
from exchanges.rfx.handlers.public import DexMarketData

from features.orderbook_imbalance import orderbook_imbalance
from features.trades_imbalance import trades_imbalance
from features.trades_diff import trades_diffs

import numpy as np
import logging


logger = logging.getLogger(__name__)


class FeatureCalculator:
    def __init__(self, compute_interval: float = 0.1): 
        self.compute_interval = compute_interval
        self.last_computed = 0.0
        
        self.depths = np.array([10.0, 25.0, 50.0, 100.0, 250.0])
        self.trade_window = 100
        self.lookback_window = 100
        
        self.weights = {
            'book_imbalance': 0.30,
            'trade_imbalance': 0.30,
            'basis': 0.25,
            'volatility': 0.15
        }

    def compute_features(self, 
                        orderbook_handler,
                        trade_handler,
                        dex_data: Optional[DexMarketData]) -> Dict:
        """Compute features from market data"""
        current_time = time.time()
        if current_time - self.last_computed < self.compute_interval:
            return None

        try:
            if not all([orderbook_handler, trade_handler, dex_data]):
                return None

            book_imbalance = orderbook_imbalance(
                bids=orderbook_handler.bids,
                asks=orderbook_handler.asks,
                depths=self.depths
            )

            trades_array = trade_handler.unwrap()
            trade_imbalance = trades_imbalance(
                trades=trades_array,
                window=self.trade_window
            )

            volatility = trades_diffs(
                trades=trades_array,
                lookback=self.lookback_window
            )

            spot_mid = (orderbook_handler.bba[0][0] + orderbook_handler.bba[1][0]) / 2
            basis = (dex_data.oracle_price - spot_mid) / spot_mid if spot_mid > 0 else 0

            skew = (
                self.weights['book_imbalance'] * book_imbalance +
                self.weights['trade_imbalance'] * trade_imbalance +
                self.weights['basis'] * basis +
                self.weights['volatility'] * -volatility
            )

            funding_adjustment = dex_data.funding_rate / (365 * 24)  
            adjusted_basis = basis - funding_adjustment
            adjusted_mid = spot_mid * (1 + adjusted_basis)

            adjusted_mid = round(float(adjusted_mid), 2)

            features = {
                'spot_mid': spot_mid,
                'dex_price': dex_data.oracle_price,
                'adjusted_mid': adjusted_mid,
                'basis': basis,
                'book_imbalance': book_imbalance,
                'trade_imbalance': trade_imbalance,
                'volatility': volatility,
                'skew': skew,
                'timestamp': current_time
            }

            self.last_computed = current_time
            return features

        except Exception as e:
            logger.error(f"Error computing features: {e}")
            return None
