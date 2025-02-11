from dataclasses import dataclass
import time
from typing import Dict, List, Optional
import asyncio
import logging

from exchanges.rfx.orders.client import OrderClient, OrderRequest, OrderSide
from oms.quote import Quote

logger = logging.getLogger(__name__)



@dataclass
class ActiveOrder:
    order_id: str
    position: int
    price: float
    size_usd: float
    side: str
    timestamp: float
    initial_collateral: float

class OrderManagementSystem:
    def __init__(self, 
                 order_client: OrderClient,
                 max_active_orders: int = 20,
                 order_timeout: float = 60.0, 
                 initial_collateral: float = 10.0,  
                 slippage_percent: float = 0.01):  
        
        self.order_client = order_client
        self.max_active_orders = max_active_orders
        self.order_timeout = order_timeout
        self.initial_collateral = initial_collateral
        self.slippage_percent = slippage_percent
        
        self.active_orders: Dict[int, ActiveOrder] = {}
        self.position_counter: int = 0

    async def process_quotes(self, quotes: List[Quote]) -> None:
        """Process new quotes and update orders"""
        try:
            await self._cancel_stale_orders()
            
            await self._cancel_mismatched_orders(quotes)
            
            await self._create_new_orders(quotes)
            
        except Exception as e:
            logger.error(f"Error processing quotes: {e}")

    async def _cancel_stale_orders(self) -> None:
        """Cancel orders that have been active too long"""
        current_time = time.time()
        positions_to_cancel = []
        
        for position, order in self.active_orders.items():
            if current_time - order.timestamp > self.order_timeout:
                positions_to_cancel.append(position)
        
        if positions_to_cancel:
            await self._cancel_orders_by_positions(positions_to_cancel)

    async def _cancel_mismatched_orders(self, new_quotes: List[Quote]) -> None:
        """Cancel orders that don't match new quotes"""
        positions_to_cancel = []
        
        for position, order in self.active_orders.items():
            matching_quote = next(
                (q for q in new_quotes if (
                    q.side == order.side and
                    abs(q.price - order.price) / order.price < 0.001 and  # 0.1% price difference
                    abs(q.size_usd - order.size_usd) / order.size_usd < 0.001  # 0.1% size difference
                )), 
                None
            )
            
            if not matching_quote:
                positions_to_cancel.append(position)
        
        if positions_to_cancel:
            await self._cancel_orders_by_positions(positions_to_cancel)

    async def _create_new_orders(self, quotes: List[Quote]) -> None:
        """Create new orders from quotes"""
        for quote in quotes:
            if len(self.active_orders) >= self.max_active_orders:
                logger.warning("Maximum active orders reached")
                break
            
            if self._quote_matches_existing(quote):
                continue
            
            try:
                order_request = OrderRequest(
                    side=OrderSide(quote.side),
                    price_usd=quote.price,
                    size_usd=quote.size_usd,
                    order_id=quote.order_id,
                    slippage_percent=self.slippage_percent
                )
                
                tx_hashes = await self.order_client.submit_order(order_request)
                
                if tx_hashes:
                    self.active_orders[self.position_counter] = ActiveOrder(
                        order_id=quote.order_id,
                        position=self.position_counter,
                        price=quote.price,
                        size_usd=quote.size_usd,
                        side=quote.side,
                        timestamp=time.time(),
                        initial_collateral=self.initial_collateral
                    )
                    self.position_counter += 1
                    
                    logger.info(f"""
                        New Order Created:
                        Position: {self.position_counter-1}
                        Side: {quote.side}
                        Price: ${quote.price:.2f}
                        Size: ${quote.size_usd:.2f}
                        Initial Collateral: ${self.initial_collateral:.2f}
                    """)
                
            except Exception as e:
                logger.error(f"Error creating order: {e}")

    async def _cancel_orders_by_positions(self, positions: List[int]) -> None:
        """Cancel orders by their positions"""
        try:
            num_to_cancel = len(positions)
            
            if num_to_cancel > 0:
                await self.order_client.cancel_orders(num_to_cancel)
                
                for pos in positions:
                    if pos in self.active_orders:
                        order = self.active_orders[pos]
                        logger.info(f"""
                            Order Cancelled:
                            Position: {pos}
                            Side: {order.side}
                            Price: ${order.price:.2f}
                            Size: ${order.size_usd:.2f}
                        """)
                        del self.active_orders[pos]
                
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")

    def _quote_matches_existing(self, quote: Quote) -> bool:
        """Check if quote matches any existing order"""
        for order in self.active_orders.values():
            if (order.side == quote.side and
                abs(order.price - quote.price) / order.price < 0.001 and
                abs(order.size_usd - quote.size_usd) / order.size_usd < 0.001):
                return True
        return False

    async def cancel_all_orders(self) -> None:
        """Cancel all active orders"""
        try:
            if self.active_orders:
                await self.order_client.cancel_orders()
                
                for pos, order in self.active_orders.items():
                    logger.info(f"""
                        Order Cancelled:
                        Position: {pos}
                        Side: {order.side}
                        Price: ${order.price:.2f}
                        Size: ${order.size_usd:.2f}
                    """)
                
                self.active_orders.clear()
                
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")

    def get_active_orders(self) -> List[ActiveOrder]:
        """Get list of active orders"""
        return list(self.active_orders.values())

    def get_order_count(self) -> int:
        """Get number of active orders"""
        return len(self.active_orders)

    def get_position_summary(self) -> str:
        """Get summary of current positions"""
        total_long_size = sum(o.size_usd for o in self.active_orders.values() 
                            if o.side in ['increase_long', 'decrease_short'])
        total_short_size = sum(o.size_usd for o in self.active_orders.values() 
                             if o.side in ['increase_short', 'decrease_long'])
        
        return f"""
        Position Summary:
        {'-' * 40}
        Total Long Size: ${total_long_size:.2f}
        Total Short Size: ${total_short_size:.2f}
        Net Position: ${total_long_size - total_short_size:.2f}
        Active Orders: {self.get_order_count()}
        {'-' * 40}
        """