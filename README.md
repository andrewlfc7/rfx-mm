# rfx-mm

## PositionHandler

Polling the rfx api to get the existing positions and send it to the invertory class to help with placing the new orders to ensure the bot isnt too over weight on the long or short.

## DexInventoryManager
Use to control the max amount of active positions so like the size for both the longs and shorts. Also control the max imbalance so like if the current short size is -10 and current long size is +30 then its going adjust the quoting to either send more shorts orders or decreasing the long positions/size to get the book back in line with the max imbalance set in the main.

## QuoteGenerator

This set the amount of orders for either side so with number of levels set to 5 set it will do 5 shorts orders and 5 longs.
total quote size control how much in the usd to use for quoting/doing the orders so it divides the number levels by the total quote size to do the size in usd for each orders, the min spread is for the setting the spread of the orders in bps and the vol impact determines how much the current vol is used to adjust the spread by.

## PublicFeed

This is the market data feed for setting up the tasks for get sub to binance ws after it uses the api to get the data and then set up another task to get the oracle and funding rate from rfx.

## OrderClient

Client for doing the orders, currently the bot is just set up for BTC, initial collateral sets how much to use for all the orders and based on the order size its handles the leverage so dont to set the leverage per order. can use debug mode = true to run the bot with actually submitting the orders.

## OrderManagementSystem

use to set the max amount of active orders we can have submitted and the order timeout set how long the orders in seconds are posted before being considered old and if its old then it will cancel those orders.

## FeatureCalculator

is used with the public feed method to compute the feature using the trade imblance and orderbook imblance to determine the skew to use in the quoting class based on the current market state.

## Example Config

```python
# position 
position_handler = PositionHandler(
    config=config, 
    symbol="BTC/USD [WETH-USDC]"
)

inventory_manager = DexInventoryManager(
    position_handler=position_handler,
    max_position=50.0,
    max_imbalance=10.0
)

# quote 
quote_generator = QuoteGenerator(
    inventory_manager=inventory_manager,
    num_levels=5,
    total_quote_size=100.0,
    min_spread=0.0001,
    vol_impact=1.0
)

# order 
order_client = OrderClient(
    config=config,
    market_symbol="BTC/USD [WETH-USDC]",
    collateral_token="USDC", 
    initial_collateral=10.0,
    debug_mode=True
)

oms = OrderManagementSystem(
    order_client=order_client,
    max_active_orders=20,
    order_timeout=60.0,
    initial_collateral=10.0,
    slippage_percent=0.01
)


to run just add wallet info in the .env file and install the packages and then cd to the src then run python3 main.py
