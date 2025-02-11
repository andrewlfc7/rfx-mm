import asyncio
from typing import Any, Optional, Dict
import logging

from exchanges.binance.feed import BinanceWebsocket
from exchanges.rfx.handlers.public import DexDataHandler, DexMarketData
from features.features import FeatureCalculator
from pyrfx.get.funding_apr import FundingAPR
from pyrfx.get.oracle_prices import OraclePrices


logger = logging.getLogger(__name__)




class PublicFeed:
    def __init__(self, 
                 symbol: str,
                 config: Any,
                 token_address: str,
                 market_symbol: str,
                 feature_compute_delay: float = 0.5): 
        
        self.binance_ws = BinanceWebsocket(symbol=symbol)
        self.dex_handler = DexDataHandler(
            symbol=symbol,
            token_address=token_address,
            market_symbol=market_symbol
        )
        
        self.feature_calculator = FeatureCalculator(compute_interval=0.1)
        
        self.config = config
        self.symbol = symbol
        self.is_running = False
        self.feature_compute_delay = feature_compute_delay
        
        self.latest_data = {
            'binance': None,
            'dex': None,
            'features': None,
            'timestamp': 0.0
        }

    async def start(self):
        """Start all data feeds and feature computation"""
        if self.is_running:
            return
        
        self.is_running = True
        
        try:
            await asyncio.gather(
                self.binance_ws.start(),
                self._poll_dex_data(),
                self._coordinate_data(),
                self._compute_features()
            )
            
        except Exception as e:
            logger.error(f"Error starting public feed: {e}")
            self.is_running = False
            raise

    async def _compute_features(self):
        """Compute features with delay to ensure data synchronization"""
        while self.is_running:
            try:
                await asyncio.sleep(self.feature_compute_delay)
                
                orderbook = self.get_orderbook()
                trades = self.get_trades()
                dex_data = self.get_dex_data()
                
                if all([orderbook, trades, dex_data]):
                    features = self.feature_calculator.compute_features(
                        orderbook_handler=orderbook,
                        trade_handler=trades,
                        dex_data=dex_data
                    )
                    
                    if features:
                        self.latest_data['features'] = features
                        
                        logger.debug(f"""
                            Features Computed:
                            Adjusted Mid: {features['adjusted_mid']:.2f}
                            Basis: {features['basis']:.6f}
                            Skew: {features['skew']:.6f}
                        """)
                
                await asyncio.sleep(0.1) 
                
            except Exception as e:
                logger.error(f"Error computing features: {e}")
                await asyncio.sleep(1)

    def get_latest_features(self) -> Optional[Dict]:
        """Get latest computed features"""
        return self.latest_data.get('features')



    async def _poll_dex_data(self):
        """Poll DEX API data"""
        while self.is_running:
            try:
                funding_task = asyncio.to_thread(
                    lambda: FundingAPR(config=self.config).get_data()
                )
                prices_task = asyncio.to_thread(
                    lambda: OraclePrices(config=self.config).get_recent_prices()
                )
                
                funding_data, prices_data = await asyncio.gather(
                    funding_task, 
                    prices_task
                )
                
                dex_data = self.dex_handler.process_data(
                    funding_data=funding_data,
                    price_data=prices_data
                )
                
                if dex_data:
                    self.latest_data['dex'] = dex_data
                    self.latest_data['timestamp'] = dex_data.timestamp
                
            except Exception as e:
                logger.error(f"Error polling DEX data: {e}")
            
            await asyncio.sleep(1)  

    async def _coordinate_data(self):
        """Coordinate and update latest data from both sources"""
        while self.is_running:
            try:
                binance_data = self.binance_ws.get_latest_data()
                if binance_data:
                    self.latest_data['binance'] = binance_data
                    
                await asyncio.sleep(0.1) 
                
            except Exception as e:
                logger.error(f"Error coordinating data: {e}")
                await asyncio.sleep(1)

    def get_orderbook(self) -> Optional[Dict]:
        """Get latest orderbook"""
        if not self.latest_data['binance']:
            return None
        return self.binance_ws.public_handler_map["depthUpdate"]

    def get_trades(self) -> Optional[Dict]:
        """Get latest trades"""
        if not self.latest_data['binance']:
            return None
        return self.binance_ws.public_handler_map["trade"]

    def get_dex_data(self) -> Optional[DexMarketData]:
        """Get latest DEX data"""
        return self.latest_data['dex']

    async def stop(self):
        """Stop all data feeds"""
        self.is_running = False
