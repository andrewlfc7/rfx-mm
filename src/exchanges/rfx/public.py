import asyncio
from typing import Any, Optional
from exchanges.rfx.handlers.public import DexDataHandler, DexMarketData

import logging
from pyrfx.config_manager import ConfigManager
from pyrfx.get.funding_apr import FundingAPR
from pyrfx.get.oracle_prices import OraclePrices


logger = logging.getLogger(__name__)


class DexDataFeed:
    def __init__(self, symbol: str, config: Any):
        self.config = config
        
        self.handler = DexDataHandler(
            symbol=symbol,
            token_address="0x00957c690A5e3f329aDb606baD99cEd9Ad701a98",  # For BTC
            market_symbol="BTC/USD [WETH-USDC]"
        )
        
        self.data_queue = asyncio.Queue()

    async def fetch_data(self):
        """Fetch data from DEX APIs"""
        funding_apr_instance = FundingAPR(config=self.config)
        oracle_prices_instance = OraclePrices(config=self.config)

        while True:
            try:
                funding_task = asyncio.to_thread(funding_apr_instance.get_data)
                prices_task = asyncio.to_thread(oracle_prices_instance.get_recent_prices)
                
                funding_apr, prices = await asyncio.gather(funding_task, prices_task)
                
                dex_data = self.handler.process_data(funding_apr, prices)
                if dex_data:
                    await self.data_queue.put(dex_data)
                
            except Exception as e:
                logger.error(f"Error fetching DEX data: {e}")
            
            await asyncio.sleep(1)

    async def get_latest_data(self) -> Optional[DexMarketData]:
        """Get latest processed data"""
        return await self.data_queue.get()
    

