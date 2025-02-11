import asyncio
import logging
from exchanges.rfx.inventory import DexInventoryManager
from exchanges.rfx.private import PositionHandler

import uvloop
from pyrfx.config_manager import ConfigManager
from typing import Any


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


config = ConfigManager(
        chain="zkSync",
        user_wallet_address="",
        private_key="",
        save_to_json=False,
        output_data_folder="logs"
     )


# async def main():
#     # Initialize position handler
#     position_handler = PositionHandler(
#         config=config,
#         symbol="BTC/USD [WETH-USDC]",
#         polling_interval=1.0
#     )
    
#     async def monitor_positions():
#         """Monitor and print position updates"""
#         while True:
#             positions = position_handler.get_positions()
#             print(f"""
# Position Update:
# Long: {positions['long']['size']:.4f} @ {positions['long']['entry_price']:.2f} (PnL: {positions['long']['pnl_percent']:.2f}%)
# Short: {positions['short']['size']:.4f} @ {positions['short']['entry_price']:.2f} (PnL: {positions['short']['pnl_percent']:.2f}%)
# Net Position: {positions['net_position']:.4f}
# Last Update: {positions['last_update']}
#             """)
#             await asyncio.sleep(1)
    
#     try:
#         # Run position polling and monitoring concurrently
#         await asyncio.gather(
#             position_handler.start(),
#             monitor_positions()
#         )
            
#     except KeyboardInterrupt:
#         logger.info("Shutting down...")
#         await position_handler.stop()
#     except Exception as e:
#         logger.error(f"Error in main: {e}")
#         await position_handler.stop()

# if __name__ == "__main__":
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )
    
#     asyncio.run(main())



# Usage example:
async def main():
    # Initialize position handler
    position_handler = PositionHandler(
        config=config,
        symbol="BTC/USD [WETH-USDC]",
        polling_interval=1.0
    )
    
    # Initialize inventory manager
    inventory_manager = DexInventoryManager(
        position_handler=position_handler,
        max_position=50.0,
        max_imbalance=10.0
    )
    
    async def monitor_inventory():
        """Monitor inventory state"""
        while True:
            # Update inventory from position handler
            inventory_manager.update_from_position_handler()
            
            # Get inventory state
            state = inventory_manager.get_inventory_state()
            
            # Print state
            print(f"""
Inventory State:
Long Position: {state['long']['size']:.4f} @ {state['long']['entry']:.2f} (PnL: {state['long']['pnl']:.2f}%)
Short Position: {state['short']['size']:.4f} @ {state['short']['entry']:.2f} (PnL: {state['short']['pnl']:.2f}%)
Net Position: {state['net_position']:.4f}
Gross Position: {state['gross_position']:.4f}
Position Skew: {state['position_skew']:.4f}
            """)
            
            await asyncio.sleep(1)
    
    try:
        # Run position polling and inventory monitoring concurrently
        await asyncio.gather(
            position_handler.start(),
            monitor_inventory()
        )
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await position_handler.stop()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        await position_handler.stop()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())