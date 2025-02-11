from dataclasses import dataclass
from typing import List, Dict, Optional
from exchanges.rfx.inventory import DexInventoryManager
import numpy as np
import logging

from utils.utils import generate_geometric_weights, geomspace


logger = logging.getLogger(__name__)



@dataclass
class Quote:
    price: float
    size: float        # Size in crypto
    size_usd: float    # Size in USD
    side: str          # 'increase_long', 'decrease_long', 'increase_short', 'decrease_short'
    order_id: str


class QuoteGenerator:
    def __init__(self,
                 inventory_manager: DexInventoryManager,
                 num_levels: int = 10,
                 total_quote_size: float = 1000.0,
                 min_spread: float = 0.001,  # 10 bps minimum spread
                 vol_impact: float = 2.0):   # Volatility impact multiplier
        
        self.inventory_manager = inventory_manager
        self.num_levels = num_levels
        self.total_quote_size = total_quote_size
        self.min_spread = min_spread
        self.vol_impact = vol_impact

    def _calculate_spread(self, volatility: float) -> float:
        """Calculate spread adjusted for volatility"""
        return max(self.min_spread * (1 + volatility * self.vol_impact), self.min_spread)

    def _adjust_skew(self, market_skew: float) -> float:
        """Adjust market skew based on inventory position"""
        position_skew = self.inventory_manager.get_position_skew()
        return 0.3 * market_skew + 0.7 * (-position_skew)  # Negative position skew for mean reversion


    def _generate_increase_long_quotes(self, mid_price: float, spread: float, larger_size: bool = True) -> List[Quote]:
        """Generate quotes to increase long position"""
        half_spread = spread / 2
        price_width = spread * 5
        
        prices = geomspace(
            mid_price * (1 - half_spread),
            mid_price * (1 - half_spread - price_width),
            self.num_levels
        )
        
        max_size_usd = self.inventory_manager.max_position - self.inventory_manager.get_gross_position()
        size_multiplier = 1.5 if larger_size else 0.5
        base_size_usd = min(self.total_quote_size, max_size_usd)
        
        size_weights = generate_geometric_weights(self.num_levels, r=0.5)
        sizes_usd = base_size_usd * size_multiplier * size_weights
        
        quotes = []
        for i, (price, size_usd) in enumerate(zip(prices, sizes_usd)):
            size_crypto = size_usd / price 
            if self.inventory_manager.can_increase_long(size_crypto):
                quotes.append(Quote(
                    price=round(float(price), 2),
                    size=round(float(size_crypto), 6),
                    size_usd=round(float(size_usd), 2),
                    side='increase_long',
                    order_id=f'long_inc_{i:02d}'
                ))
        
        return quotes

    def _generate_increase_short_quotes(self, mid_price: float, spread: float, larger_size: bool = True) -> List[Quote]:
        """Generate quotes to increase short position"""
        half_spread = spread / 2
        price_width = spread * 5
        
        prices = geomspace(
            mid_price * (1 + half_spread),
            mid_price * (1 + half_spread + price_width),
            self.num_levels
        )
        
        max_size_usd = self.inventory_manager.max_position - self.inventory_manager.get_gross_position()
        size_multiplier = 1.5 if larger_size else 0.5
        base_size_usd = min(self.total_quote_size, max_size_usd)
        
        size_weights = generate_geometric_weights(self.num_levels, r=0.5)
        sizes_usd = base_size_usd * size_multiplier * size_weights
        
        quotes = []
        for i, (price, size_usd) in enumerate(zip(prices, sizes_usd)):
            size_crypto = size_usd / price  
            if self.inventory_manager.can_increase_short(size_crypto):
                quotes.append(Quote(
                    price=round(float(price), 2),
                    size=round(float(size_crypto), 6),
                    size_usd=round(float(size_usd), 2),
                    side='increase_short',
                    order_id=f'short_inc_{i:02d}'
                ))
        
        return quotes

    def _generate_decrease_long_quotes(self, mid_price: float, spread: float) -> List[Quote]:
        """Generate quotes to decrease long position"""
        current_long = self.inventory_manager.position.long_size
        if current_long <= 0:
            return []
            
        half_spread = spread / 2
        price_width = spread * 3
        
        prices = geomspace(
            mid_price * (1 + half_spread),
            mid_price * (1 + half_spread + price_width),
            self.num_levels
        )
        
        size_per_level_crypto = current_long / self.num_levels
        
        quotes = []
        for i, price in enumerate(prices):
            size_usd = size_per_level_crypto * price
            quotes.append(Quote(
                price=round(float(price), 2),
                size=round(float(size_per_level_crypto), 6),
                size_usd=round(float(size_usd), 2),
                side='decrease_long',
                order_id=f'long_dec_{i:02d}'
            ))
        
        return quotes

    def _generate_decrease_short_quotes(self, mid_price: float, spread: float) -> List[Quote]:
        """Generate quotes to decrease short position"""
        current_short = self.inventory_manager.position.short_size
        if current_short <= 0:
            return []
            
        half_spread = spread / 2
        price_width = spread * 3
        
        prices = geomspace(
            mid_price * (1 - half_spread),
            mid_price * (1 - half_spread - price_width),
            self.num_levels
        )
        
        size_per_level_crypto = current_short / self.num_levels
        
        quotes = []
        for i, price in enumerate(prices):
            size_usd = size_per_level_crypto * price
            quotes.append(Quote(
                price=round(float(price), 2),
                size=round(float(size_per_level_crypto), 6),
                size_usd=round(float(size_usd), 2),
                side='decrease_short',
                order_id=f'short_dec_{i:02d}'
            ))
        
        return quotes



    def generate_quotes(self, features: Dict) -> List[Quote]:
        """Generate quotes based on market features and inventory"""
        try:
            if not features:
                return []

            adjusted_mid = features['adjusted_mid']
            market_skew = features['skew']
            volatility = features['volatility']
            
            spread = self._calculate_spread(volatility)
            
            total_skew = self._adjust_skew(market_skew)
            
            quotes = []
            
            # If negative skew (selling pressure)
            if total_skew < 0:
                # Add more short exposure
                quotes.extend(self._generate_increase_short_quotes(
                    adjusted_mid, spread, larger_size=True
                ))
                
                # Reduce long exposure if exists
                quotes.extend(self._generate_decrease_long_quotes(
                    adjusted_mid, spread
                ))
                
                # Add minimal long exposure
                quotes.extend(self._generate_increase_long_quotes(
                    adjusted_mid, spread, larger_size=False
                ))
                
            # If positive skew (buying pressure)
            elif total_skew > 0:
                # Add more long exposure
                quotes.extend(self._generate_increase_long_quotes(
                    adjusted_mid, spread, larger_size=True
                ))
                
                # Reduce short exposure if exists
                quotes.extend(self._generate_decrease_short_quotes(
                    adjusted_mid, spread
                ))
                
                # Add minimal short exposure
                quotes.extend(self._generate_increase_short_quotes(
                    adjusted_mid, spread, larger_size=False
                ))
                
            # If neutral skew
            else:
                quotes.extend(self._generate_increase_long_quotes(
                    adjusted_mid, spread, larger_size=True
                ))
                quotes.extend(self._generate_increase_short_quotes(
                    adjusted_mid, spread, larger_size=True
                ))
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error generating quotes: {e}")
            return []
        

