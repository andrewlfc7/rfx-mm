from dataclasses import dataclass
from typing import Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class DexPosition:
    """Track position and related metrics"""
    long_size: float = 0.0
    short_size: float = 0.0
    long_entry: float = 0.0
    short_entry: float = 0.0
    long_pnl: float = 0.0
    short_pnl: float = 0.0
    last_update: float = 0.0

class DexInventoryManager:
    def __init__(self, 
                 position_handler,
                 max_position: float = 50.0,
                 max_imbalance: float = 10.0):
        
        self.position_handler = position_handler
        self.max_position = max_position
        self.max_imbalance = max_imbalance
        self.position = DexPosition()
        
        self.update_from_position_handler()

    def update_from_position_handler(self) -> None:
        """Update inventory state from position handler"""
        try:
            positions = self.position_handler.get_positions()
            
            self.position.long_size = positions['long']['size']
            self.position.long_entry = positions['long']['entry_price']
            self.position.long_pnl = positions['long']['pnl_percent']
            

            self.position.short_size = positions['short']['size']
            self.position.short_entry = positions['short']['entry_price']
            self.position.short_pnl = positions['short']['pnl_percent']
            
            self.position.last_update = positions['last_update']
            
            logger.info(f"""
                Inventory Updated:
                Long: {self.position.long_size:.4f} @ {self.position.long_entry:.2f} (PnL: {self.position.long_pnl:.2f}%)
                Short: {self.position.short_size:.4f} @ {self.position.short_entry:.2f} (PnL: {self.position.short_pnl:.2f}%)
                Net: {self.get_net_position():.4f}
            """)
            
        except Exception as e:
            logger.error(f"Error updating inventory: {e}")

    def get_net_position(self) -> float:
        """Get net position"""
        return self.position.long_size - self.position.short_size

    def get_gross_position(self) -> float:
        """Get gross position"""
        return self.position.long_size + self.position.short_size

    def can_increase_long(self, size: float) -> bool:
        """Check if can increase long position"""
        new_long = self.position.long_size + size
        new_gross = new_long + self.position.short_size
        new_net = new_long - self.position.short_size
        
        return (new_gross <= self.max_position and 
                abs(new_net) <= self.max_imbalance)

    def can_increase_short(self, size: float) -> bool:
        """Check if can increase short position"""
        new_short = self.position.short_size + size
        new_gross = self.position.long_size + new_short
        new_net = self.position.long_size - new_short
        
        return (new_gross <= self.max_position and 
                abs(new_net) <= self.max_imbalance)

    def get_position_skew(self) -> float:
        """Calculate position skew for quote adjustment"""
        net_position = self.get_net_position()
        return -net_position / self.max_imbalance  # Negative because we want to mean revert

    def get_inventory_state(self) -> Dict:
        """Get current inventory state"""
        return {
            'long': {
                'size': self.position.long_size,
                'entry': self.position.long_entry,
                'pnl': self.position.long_pnl
            },
            'short': {
                'size': self.position.short_size,
                'entry': self.position.short_entry,
                'pnl': self.position.short_pnl
            },
            'net_position': self.get_net_position(),
            'gross_position': self.get_gross_position(),
            'position_skew': self.get_position_skew(),
            'last_update': self.position.last_update
        }
