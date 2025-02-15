from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from hexbytes import HexBytes
import logging
from pyrfx.custom_error_parser import CustomErrorParser
from pyrfx.order.limit_cancel import LimitCancelOrder
from pyrfx.config_manager import ConfigManager
from pyrfx.order.limit_increase import LimitIncreaseOrder
from pyrfx.order.decrease import DecreaseOrder
from pyrfx.order.arg_parser_order import OrderArgumentParser



logger = logging.getLogger(__name__)

class OrderSide(Enum):
    INCREASE_LONG = "increase_long"
    INCREASE_SHORT = "increase_short"
    DECREASE_LONG = "decrease_long"
    DECREASE_SHORT = "decrease_short"

@dataclass
class OrderRequest:
    side: OrderSide
    price_usd: float
    size_usd: float
    order_id: str
    slippage_percent: float = 0.01  # Default 1% slippage

class OrderClient:
    def __init__(self, 
                 config: ConfigManager,
                 market_symbol: str = "BTC/USD [WETH-USDC]",
                 collateral_token: str = "USDC",
                 initial_collateral: float = 5.0,  # Fixed initial collateral for all orders
                 debug_mode: bool = True):
        
        self.config = config
        self.market_symbol = market_symbol
        self.collateral_token = collateral_token
        self.initial_collateral = initial_collateral
        self.debug_mode = debug_mode
        
        # Initialize parsers with specific operation types
        self.increase_parser = OrderArgumentParser(config=config, operation_type="limit_increase")
        self.decrease_parser = OrderArgumentParser(config=config, operation_type="decrease")
        self.error_parser = CustomErrorParser(config=config)
        
        # Track open orders
        self.open_orders: Dict[str, OrderRequest] = {}

    async def submit_order(self, order: OrderRequest) -> Optional[Dict[str, HexBytes]]:
        """Submit an order to the exchange"""
        try:
            if order.side in [OrderSide.INCREASE_LONG, OrderSide.INCREASE_SHORT]:
                return await self._submit_limit_increase(order)
            else:
                return await self._submit_market_decrease(order)
                
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            self._handle_error(e)
            return None

    async def _submit_limit_increase(self, order: OrderRequest) -> Optional[Dict[str, HexBytes]]:
        """Submit a limit increase order"""
        try:
            # Prepare order parameters
            parameters = {
                "selected_market": self.market_symbol,
                "collateral_token_symbol": self.collateral_token,
                "start_token_symbol": self.collateral_token,
                "position_type": "long" if order.side == OrderSide.INCREASE_LONG else "short",
                "size_delta_usd": order.size_usd,
                "initial_collateral_delta": self.initial_collateral,  # Use fixed initial collateral
                "trigger_price": order.price_usd,
                "slippage_percent": order.slippage_percent
            }

            # Process parameters
            order_parameters = self.increase_parser.process_parameters(parameters=parameters)

            # Create and execute order
            limit_order = LimitIncreaseOrder(
                config=self.config,
                market_address=order_parameters["market_address"],
                collateral_address=order_parameters["start_token_address"],
                index_token_address=order_parameters["index_token_address"],
                is_long=(order_parameters["position_type"] == "long"),
                size_delta=order_parameters["size_delta"],
                initial_collateral_delta=order_parameters["initial_collateral_delta"],
                trigger_price=order_parameters["trigger_price"],
                slippage_percent=order_parameters["slippage_percent"],
                debug_mode=self.debug_mode
            )

            # Execute order and track it
            tx_hashes = limit_order.create_and_execute()
            if tx_hashes:
                self.open_orders[order.order_id] = order
            
            return tx_hashes

        except Exception as e:
            logger.error(f"Error submitting limit increase order: {e}")
            self._handle_error(e)
            return None

    async def _submit_market_decrease(self, order: OrderRequest) -> Optional[Dict[str, HexBytes]]:
        """Submit a market decrease order"""
        try:
            # Prepare order parameters
            parameters = {
                "selected_market": self.market_symbol,
                "collateral_token_symbol": self.collateral_token,
                "start_token_symbol": self.collateral_token,
                "position_type": "long" if order.side == OrderSide.DECREASE_LONG else "short",
                "size_delta_usd": order.size_usd,
                "initial_collateral_delta": self.initial_collateral,  # Use fixed initial collateral
                "slippage_percent": order.slippage_percent
            }

            # Process parameters
            order_parameters = self.decrease_parser.process_parameters(parameters=parameters)

            # Create and execute order
            decrease_order = DecreaseOrder(
                config=self.config,
                market_address=order_parameters["market_address"],
                collateral_address=order_parameters["collateral_address"],
                index_token_address=order_parameters["index_token_address"],
                is_long=(order_parameters["position_type"] == "long"),
                size_delta=order_parameters["size_delta"],
                initial_collateral_delta=order_parameters["initial_collateral_delta"],
                slippage_percent=order_parameters["slippage_percent"],
                debug_mode=self.debug_mode
            )

            return decrease_order.create_and_execute()

        except Exception as e:
            logger.error(f"Error submitting market decrease order: {e}")
            self._handle_error(e)
            return None

    async def cancel_orders(self, num_orders: int = None) -> None:
        """Cancel open orders"""
        try:
            cancel_order = LimitCancelOrder(
                config=self.config,
                debug_mode=self.debug_mode
            )

            # List current orders
            cancel_order.list_orders()

            # Cancel specified number of orders or all if not specified
            num_to_cancel = num_orders if num_orders else len(self.open_orders)
            
            for _ in range(num_to_cancel):
                tx_hashes = cancel_order.create_and_execute()
                if tx_hashes:
                    for k, v in tx_hashes.items():
                        logger.info(f"Cancelled order - {k}: {v.hex()}")

            # Clear tracked orders
            self.open_orders.clear()

        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """Handle order execution errors"""
        try:
            if error.args:
                error_reason = self.error_parser.parse_error(error_bytes=error.args[0])
                error_message = self.error_parser.get_error_string(error_reason=error_reason)
                logger.error(f"Order execution error: {error_message}")
        except Exception as e:
            logger.error(f"Error parsing execution error: {e}")