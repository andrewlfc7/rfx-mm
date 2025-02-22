# rfx-mm

## PositionHandler

Polling the RFX API to get existing positions and sending them to the inventory manager to help with placing new orders while making sure the bot isn’t too overweight on long or short positions.

## DexInventoryManager

Used to control the max number of active positions for both longs and shorts. Also manages max imbalance—so if the current short size is -10 and long size is +30, it adjusts quoting to either send more short orders or decrease long positions to bring things back in line with the max imbalance set in the config.

## QuoteGenerator

Controls the number of bid/ask levels. If set to 5, it will create 5 short orders and 5 long orders. The total quote size determines how much USD to use for quoting, dividing it across the levels to set order sizes. The min spread sets the order spread in bps, and vol impact adjusts the spread based on market volatility.

## PublicFeed

Handles the market data feed, subscribing to Binance WebSocket after using the API to get initial data. Also sets up a task to fetch oracle and funding rates from RFX.

## OrderClient

Handles order execution. Currently, the bot is set up for BTC. Initial collateral sets how much to use for all orders, and leverage is managed automatically based on order size, so you don’t need to set it per order. `debug_mode=True` can be used to run the bot without actually submitting orders.

## OrderManagementSystem

Manages active orders, setting a limit on the number of open orders. `order_timeout` defines how long orders stay active before they’re considered old and canceled.

## FeatureCalculator

Uses market data from PublicFeed to compute trade and order book imbalances. Helps determine the skew for quoting based on the current market state.

---

## Setup & Running

1. Add wallet info in `.env`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Modify `parameters.yaml` to configure bot settings.
4. Navigate to `src` and run:
   ```bash
   python3 main.py
   ```

---

## Configuration

All of the bot config setting are stored in the  `parameters.yaml`

Also, the bot is currently set up for BTC since it has the most liquidity on RFX, but it can be easily tweaked for other coins. Just make sure the coin is also traded on Binance.


`parameters.yaml`:
```yaml

public_feed:
  symbol: "btcusdt"
  token_address: "0x00957c690A5e3f329aDb606baD99cEd9Ad701a98"
  market_symbol: "BTC/USD [WETH-USDC]"
  feature_compute_delay: 0.5

inventory:
  max_position: 50.0
  max_imbalance: 10.0

quote:
  num_levels: 5
  total_quote_size: 100.0
  min_spread: 0.0001
  vol_impact: 1.0

order:
  market_symbol: "BTC/USD [WETH-USDC]"
  collateral_token: "USDC"
  initial_collateral: 10.0
  debug_mode: true

oms:
  max_active_orders: 20
  order_timeout: 60.0
  slippage_percent: 0.01
```


## Docker set up 

```bash

To run the bot using docker, first tweak parameter config for setting bot's config and then ensure that docker and docker-compose is installed. Then can run the following commands to build the docker container ; 

cd rfx-mm

sudo docker-compose build

if there's an problem with getting the python image can use this to pull the image first : docker pull python:3.11.4-slim

After the build completes, add the wallet info with: USER_WALLET_ADDRESS= PRIVATE_KEY= docker-compose up 

the command above will let you see all of the logs in the terminal but can add -d at the end of it to run in detach mode.

```


## Without Docker

Just refer to the Setup & Running sections to run the bot without using docker 

