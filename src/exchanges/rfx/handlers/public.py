from dataclasses import dataclass
import time
from typing import Dict, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

@dataclass
class DexMarketData:
    """Processed DEX market data"""
    symbol: str
    oracle_price: float
    funding_rate: float  # Combined funding rate
    timestamp: float

class DexDataHandler:
    def __init__(self, symbol: str, token_address: str, market_symbol: str):
        """
        Initialize DEX data handler
        
        Parameters:
        - symbol: Trading symbol (e.g., 'BTC')
        - token_address: Token address on DEX
        - market_symbol: Market symbol on DEX (e.g., 'BTC/USD [WETH-USDC]')
        """
        self.symbol = symbol
        self.token_address = token_address
        self.market_symbol = market_symbol
        
        # self.token_address = "0x00957c690A5e3f329aDb606baD99cEd9Ad701a98"
        # self.market_symbol = "BTC/USD [WETH-USDC]"

    def _convert_wei_to_float(self, wei_value: str, decimals: int = 22) -> float:
        """Convert wei string to float"""
        try:
            value = Decimal(wei_value) / Decimal(10 ** decimals)
            return float(value)
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting price: {e}")
            return 0.0

    def _combine_funding_rates(self, long_rate: float, short_rate: float) -> float:
        """
        Combine long and short funding rates into a single rate
        Using average magnitude with sign from long rate
        """
        try:
            # Calculate average magnitude
            avg_magnitude = (abs(long_rate) + abs(short_rate)) / 2
            # Apply sign from long rate
            return avg_magnitude if long_rate >= 0 else -avg_magnitude
        except Exception as e:
            logger.error(f"Error combining funding rates: {e}")
            return 0.0

    def process_funding_rates(self, funding_data: Dict) -> float:
        """Process funding rate data for symbol"""
        try:
            # Extract long and short rates
            long_rate = funding_data['long'].get(self.market_symbol, 0.0)
            short_rate = funding_data['short'].get(self.market_symbol, 0.0)
            
            # Combine rates
            return self._combine_funding_rates(long_rate, short_rate)
            
        except Exception as e:
            logger.error(f"Error processing funding rates: {e}")
            return 0.0

    def process_oracle_price(self, price_data: Dict) -> float:
        """Process oracle price data for symbol"""
        try:
            token_data = price_data.get(self.token_address)
            if not token_data:
                return 0.0
            
            # Get max and min prices
            max_price = self._convert_wei_to_float(token_data['maxPriceFull'])
            min_price = self._convert_wei_to_float(token_data['minPriceFull'])
            
            # Return average price
            return (max_price + min_price) / 2
            
        except Exception as e:
            logger.error(f"Error processing oracle price: {e}")
            return 0.0

    def process_data(self, funding_data: Dict, price_data: Dict) -> Optional[DexMarketData]:
        """Process both funding and price data"""
        try:
            # Process funding rates
            funding_rate = self.process_funding_rates(funding_data)
            
            # Process oracle price
            oracle_price = self.process_oracle_price(price_data)
            
            if oracle_price == 0:
                logger.warning(f"Got zero oracle price for {self.symbol}")
                return None
            
            return DexMarketData(
                symbol=self.symbol,
                oracle_price=oracle_price,
                funding_rate=funding_rate,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            return None
