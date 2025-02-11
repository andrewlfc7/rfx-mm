import asyncio
from typing import Dict, Optional
import time
from dataclasses import dataclass
from pyrfx.get.open_positions import OpenPositions
import logging

logger = logging.getLogger(__name__)

@dataclass
class Position:
    size: float = 0.0
    entry_price: float = 0.0
    mark_price: float = 0.0
    pnl_percent: float = 0.0
    last_update: float = 0.0

class PositionHandler:
    def __init__(self, 
                 config: Dict,
                 symbol: str,
                 polling_interval: float = 1.0):  
        
        self.config = config
        self.symbol = symbol  
        self.polling_interval = polling_interval
        self.is_running = False
        
        self.long_position = Position()
        self.short_position = Position()
        
        self.position_client = OpenPositions(config=self.config)
        
        self.last_update_time = 0.0

    async def start(self):
        """Start position polling"""
        self.is_running = True
        await self.poll_positions()

    async def stop(self):
        """Stop position polling"""
        self.is_running = False

    async def poll_positions(self):
        """Continuously poll for position updates"""
        while self.is_running:
            try:
                position_data = await self._fetch_positions()
                
                if position_data:
                    await self._process_positions(position_data)
                    
                    self._log_positions()
                
                await asyncio.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Error polling positions: {e}")
                await asyncio.sleep(self.polling_interval)

    async def _fetch_positions(self) -> Optional[Dict]:
        """Fetch position data from DEX"""
        try:
            position_data = await asyncio.get_event_loop().run_in_executor(
                None,
                self.position_client.get_open_positions
            )
            return position_data
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return None

    async def _process_positions(self, position_data: Dict):
        """Process position data"""
        try:
            long_key = f"{self.symbol}_long"
            if long_key in position_data:
                long_data = position_data[long_key]
                self.long_position = Position(
                    size=float(long_data['position_size']),
                    entry_price=float(long_data['entry_price']),
                    mark_price=float(long_data['mark_price']),
                    pnl_percent=float(long_data['percent_profit']),
                    last_update=time.time()
                )
            else:
                self.long_position = Position()
            
            short_key = f"{self.symbol}_short"
            if short_key in position_data:
                short_data = position_data[short_key]
                self.short_position = Position(
                    size=float(short_data['position_size']),
                    entry_price=float(short_data['entry_price']),
                    mark_price=float(short_data['mark_price']),
                    pnl_percent=float(short_data['percent_profit']),
                    last_update=time.time()
                )
            else:
                self.short_position = Position()
            
            self.last_update_time = time.time()
            
        except Exception as e:
            logger.error(f"Error processing positions: {e}")

    def get_positions(self) -> Dict:
        """Get current position state"""
        return {
            'long': {
                'size': self.long_position.size,
                'entry_price': self.long_position.entry_price,
                'mark_price': self.long_position.mark_price,
                'pnl_percent': self.long_position.pnl_percent
            },
            'short': {
                'size': self.short_position.size,
                'entry_price': self.short_position.entry_price,
                'mark_price': self.short_position.mark_price,
                'pnl_percent': self.short_position.pnl_percent
            },
            'net_position': self.long_position.size - self.short_position.size,
            'last_update': self.last_update_time
        }

    def _log_positions(self):
        """Log position updates"""
        positions = self.get_positions()
        logger.info(f"""
            Positions Update:
            Long: {positions['long']['size']:.4f} @ {positions['long']['entry_price']:.2f} ({positions['long']['pnl_percent']:.2f}%)
            Short: {positions['short']['size']:.4f} @ {positions['short']['entry_price']:.2f} ({positions['short']['pnl_percent']:.2f}%)
            Net: {positions['net_position']:.4f}
        """)
