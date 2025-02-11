import asyncio
import logging
from exchanges.rfx.private import PositionHandler
from exchanges.rfx.public import DexDataFeed
from feed.market_data import PublicFeed
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
#     public_feed = PublicFeed(
#         symbol="btcusdt",
#         config=config,  
#         token_address="0x00957c690A5e3f329aDb606baD99cEd9Ad701a98", 
#         market_symbol="BTC/USD [WETH-USDC]"
#     )
    
#     async def monitor_data():
#         """Monitor and print data from feeds"""
#         while True:
#             try:
#                 # Get latest data
#                 orderbook = public_feed.get_orderbook()
#                 trades = public_feed.get_trades()
#                 dex_data = public_feed.get_dex_data()
#                 print(orderbook.bids[0])
#                 print(dex_data)
#                 print(trades)
                
#                 if all([orderbook, dex_data]):
#                     logger.info(f"""
#                         Latest Data:
#                         Orderbook Best Bid: {orderbook.bids[0] if len(orderbook.bids) > 0 else None}
#                         DEX Price: {dex_data.oracle_price}
#                         Funding Rate: {dex_data.funding_rate}
#                     """)
                
#                 await asyncio.sleep(1)
                
#             except Exception as e:
#                 logger.error(f"Error monitoring data: {e}")
#                 await asyncio.sleep(1)
    
#     try:
#         # Start both feed and monitoring concurrently
#         await asyncio.gather(
#             public_feed.start(),
#             monitor_data()
#         )
            
#     except KeyboardInterrupt:
#         await public_feed.stop()
#     except Exception as e:
#         logger.error(f"Error in main: {e}")
#         await public_feed.stop()

# if __name__ == "__main__":
#     # Configure logging
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )
    
#     # Run the main function
#     asyncio.run(main())




# # Usage example
# async def main():
#     public_feed = PublicFeed(
#         symbol="btcusdt",
#         config=config,
#         token_address="0x00957c690A5e3f329aDb606baD99cEd9Ad701a98",
#         market_symbol="BTC/USD [WETH-USDC]",
#         feature_compute_delay=0.5
#     )
    
#     async def monitor_features():
#         while True:
#             features = public_feed.get_latest_features()
#             print(features)
#             if features:
#                 logger.info(f"""
#                     Latest Features:
#                     Adjusted Mid: {features['adjusted_mid']:.2f}
#                     Basis: {features['basis']:.6f}
#                     Book Imbalance: {features['book_imbalance']:.6f}
#                     Trade Imbalance: {features['trade_imbalance']:.6f}
#                     Skew: {features['skew']:.6f}
#                 """)
#             await asyncio.sleep(1)
    
#     try:
#         await asyncio.gather(
#             public_feed.start(),
#             monitor_features()
#         )
#     except KeyboardInterrupt:
#         await public_feed.stop()
#     except Exception as e:
#         logger.error(f"Error in main: {e}")
#         await public_feed.stop()

# asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

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
    
    try:
        # Start position polling
        await position_handler.start()
        
        # Your main trading loop
        while True:
            # Get current positions
            positions = position_handler.get_positions()
            
            # Use position data for trading decisions
            print(f"Current Positions: {positions}")
            
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        await position_handler.stop()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        await position_handler.stop()

if __name__ == "__main__":
    asyncio.run(main())