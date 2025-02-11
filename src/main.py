import asyncio
import logging
from exchanges.rfx.inventory import DexInventoryManager
from exchanges.rfx.orders.client import OrderClient
from exchanges.rfx.private import PositionHandler
from exchanges.rfx.public import DexDataFeed
from feed.market_data import PublicFeed
from oms.oms import OrderManagementSystem
from oms.quote import  QuoteGenerator
import uvloop
from pyrfx.config_manager import ConfigManager
from typing import Any


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger(__name__)


config = ConfigManager(
        chain="zkSync",
        user_wallet_address="",
        private_key="",
        save_to_json=False
     )


async def main():
    try:
        logger.info("Initializing market maker components...")

        position_handler = PositionHandler(
            config=config, 
            symbol="BTC/USD [WETH-USDC]"
        )
        logger.info("Position handler initialized")
        
        inventory_manager = DexInventoryManager(
            position_handler=position_handler,
            max_position=50.0,
            max_imbalance=10.0
        )
        logger.info("Inventory manager initialized")
        
        quote_generator = QuoteGenerator(
            inventory_manager=inventory_manager,
            num_levels=5,
            total_quote_size=100.0,
            min_spread=0.0001,  
            vol_impact=1.0
        )
        logger.info("Quote generator initialized")

        public_feed = PublicFeed(
            symbol="btcusdt",
            config=config,
            token_address="0x00957c690A5e3f329aDb606baD99cEd9Ad701a98",
            market_symbol="BTC/USD [WETH-USDC]",
            feature_compute_delay=0.5
        )
        logger.info("Public feed initialized")

        order_client = OrderClient(
            config=config,
            market_symbol="BTC/USD [WETH-USDC]",
            collateral_token="USDC",
            initial_collateral=5.0,
            debug_mode=False
        )
        logger.info("Order client initialized")
        
        oms = OrderManagementSystem(
            order_client=order_client,
            max_active_orders=20,
            order_timeout=60.0,
            initial_collateral=5,
            slippage_percent=0.01
        )
        logger.info("Order management system initialized")

        async def monitor_quotes():
            logger.info("Starting quote monitoring...")
            while True:
                try:
                    inventory_manager.update_from_position_handler()
                    
                    features = public_feed.get_latest_features()
                    if features:
                        logger.debug(f"Features received: {features}")
                        
                        quotes = quote_generator.generate_quotes(features)
                        if quotes:
                            await oms.process_quotes(quotes)
                            
                            logger.info(f"""
                                Market State:
                                {'-' * 40}
                                Mid Price: ${features['adjusted_mid']:.2f}
                                Market Skew: {features['skew']:.4f}
                                Volatility: {features['volatility']:.4f}
                                
                                {oms.get_position_summary()}
                                
                                Active Orders:
                                {'-' * 40}
                                {'Position':>8} | {'Side':>12} | {'Price':>10} | {'Size USD':>12}
                                {'-' * 40}
                                {chr(10).join(
                                    f"{order.position:8d} | {order.side:12s} | {order.price:10.2f} | ${order.size_usd:10.2f}"
                                    for order in oms.get_active_orders()
                                )}
                            """)
                    
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error in quote monitoring: {e}")
                    await asyncio.sleep(1)

        async def shutdown():
            """Graceful shutdown procedure"""
            logger.info("Initiating shutdown...")
            
            await oms.cancel_all_orders()
            logger.info("All orders cancelled")
            
            await position_handler.stop()
            logger.info("Position handler stopped")
            
            await public_feed.stop()
            logger.info("Public feed stopped")
            
            logger.info("Shutdown complete")

        try:
            logger.info("Starting market maker...")
            await asyncio.gather(
                position_handler.start(),
                public_feed.start(),
                monitor_quotes()
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            await shutdown()
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await shutdown()

    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('market_maker.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
