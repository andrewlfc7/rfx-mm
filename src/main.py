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
from utils.env import get_env_vars
import yaml

logger = logging.getLogger(__name__)

env_vars = get_env_vars()


with open("parameters.yaml", "r") as file:
    parameters = yaml.safe_load(file)


config = ConfigManager(
    chain="zkSync",
    user_wallet_address=env_vars["USER_WALLET_ADDRESS"],
    private_key=env_vars["PRIVATE_KEY"],
    save_to_json=False
)


async def main():
    try:
        logger.info("Initializing market maker components...")

        position_handler = PositionHandler(
            config=config, 
            symbol=parameters['public_feed']['market_symbol']
        )
        logger.info("Position handler initialized")
        
        inventory_manager = DexInventoryManager(
            position_handler=position_handler,
            max_position=parameters["inventory"]["max_position"],
            max_imbalance=parameters["inventory"]["max_imbalance"]
        )
        logger.info("Inventory manager initialized")
        

        quote_generator = QuoteGenerator(
            inventory_manager=inventory_manager,
            num_levels=parameters["quote"]["num_levels"],
            total_quote_size=parameters["quote"]["total_quote_size"],
            min_spread=parameters["quote"]["min_spread"],
            vol_impact=parameters["quote"]["vol_impact"]
        )


        logger.info("Quote generator initialized")

        public_feed = PublicFeed(
            symbol=parameters['public_feed']['symbol'],
            config=config,
            token_address=parameters['public_feed']['token_address'],
            market_symbol=parameters['public_feed']['market_symbol'],
            feature_compute_delay=parameters['public_feed']['feature_compute_delay']
        )
        logger.info("Public feed initialized")

        order_client = OrderClient(
            config=config,
            market_symbol=parameters["order"]["market_symbol"],
            collateral_token=parameters["order"]["collateral_token"],
            initial_collateral=parameters["order"]["initial_collateral"],
            debug_mode=parameters["order"]["debug_mode"]
        )
        logger.info("Order client initialized")

        oms = OrderManagementSystem(
            order_client=order_client,
            max_active_orders=parameters["oms"]["max_active_orders"],
            order_timeout=parameters["oms"]["order_timeout"],
            slippage_percent=parameters["oms"]["slippage_percent"]
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
