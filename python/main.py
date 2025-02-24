import asyncio
import aiohttp
from decimal import Decimal
import time
from typing import Optional
from pydantic import BaseModel, ValidationError, validator

# Constants
API_ENDPOINT = 'https://alphainsider.com/api'
API_KEY = ''  # Replace with your API key
STRATEGY_ID = ''  # Replace with your strategy ID

# Initial positions
positions = [
    {"symbol": "USD", "amount": "1000"},
    {"symbol": "BTC", "amount": "0.1"}
]

# newOrderParams <stock_id> <action> <type> --amount-- --total-- --price-- --stop_price--
class NewOrderParams(BaseModel):
    stock_id: str
    action: str
    type: str
    amount: Optional[str] = None
    total: Optional[str] = None
    price: Optional[float] = None
    stop_price: Optional[float] = None

    @validator('stock_id')
    def stock_id_not_usd(cls, v):
        if v in ['ubfhvYUsgvMIuJPwr76My', 'USD:ALPHAINSIDER']:
            raise ValueError('Invalid stock_id')
        return v

    @validator('action')
    def action_valid(cls, v):
        if v not in ['buy', 'sell']:
            raise ValueError('Invalid action')
        return v

    @validator('type')
    def type_valid(cls, v):
        if v not in ['limit', 'stop_limit', 'stop_market', 'market', 'oco']:
            raise ValueError('Invalid type')
        return v

# Helper functions

# getStrategy
# Example Response: {"strategy_id":"YdNf91nP-Q-YB39RwtlHQ","product_id":"yvtLPHMNML3th6csjO_bV","user_id":"user_1","type":"cryptocurrency","private":false,"name":"vdsvdsvds","description":"","updated_at":"2024-10-07T15:05:09.124Z","created_at":"2024-10-07T15:05:09.124Z","price":0,"subscriber_count":"0","timeframes":[{"timeframe":"week","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"year","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"day","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"month","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"five_year","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"}]}
async def get_strategy():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_ENDPOINT}/getStrategies",
            headers={"authorization": API_KEY},
            params={"strategy_id": [STRATEGY_ID]},
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            data = await response.json()
            if not data["response"] or not isinstance(data["response"], list):
                raise ValueError("Strategy response is invalid")
            return data["response"][0]

# getStrategyValue
# Example Response: {"strategy_id":"PKw1UvPIoGMARkXTXzYk6","strategy_value":"1.00000000000000000"}
async def get_strategy_value():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_ENDPOINT}/getStrategyValues",
            headers={"authorization": API_KEY},
            params={"strategy_id": [STRATEGY_ID]},
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            data = await response.json()
            if not data["response"] or not isinstance(data["response"], list):
                raise ValueError("Strategy value response is invalid")
            return data["response"][0]

# getPositions
# Example Response: [{"position_id":"PAiBXHzE10Fa4ioITCXbX","strategy_id":"7Wy5AzIKY9bCmkIqjcLSg","type":"liability","price":"1.000000000000000","amount":"-0.932626292686600","total":"-0.932626292686600","updated_at":"2024-07-18T20:14:44.660Z","created_at":"2024-07-18T20:14:44.660Z","stock_id":"ubfhvYUsgvMIuJPwr76My","figi_composite":null,"symbol":"USD","name":"US Dollar","sector":"Unallocated","security":"","exchange":"ALPHAINSIDER","stock":"USD","peg":"USD","provider":"alphainsider","slippage":"0.000000000000000","fee":"0.000000000000000","links":{},"stock_status":"active","bid":"1.000000000000000","ask":"1.000000000000000","last":"1.000000000000000"},{"position_id":"XoLx1OyDdRBr_yq4JHJdB","strategy_id":"7Wy5AzIKY9bCmkIqjcLSg","type":"asset","price":"2996.940000000000000","amount":"0.000647643919923","total":"1.940949969374036","updated_at":"2024-07-18T20:14:44.660Z","created_at":"2024-05-08T19:51:06.230Z","stock_id":"v3lhjrwEhNuAOxPT29oxO","figi_composite":null,"symbol":"ETH-USD","name":"Ethereum","sector":"Cryptocurrencies","security":"cryptocurrency","exchange":"COINBASE","stock":"ETH","peg":"USD","provider":"coinbase","slippage":"0.000000000000000","fee":"0.002500000000000","links":{"trading_view":"https://www.tradingview.com/symbols/ETHUSD/?exchange=COINBASE","yahoo_finance":"https://finance.yahoo.com/quote/ETH-USD","coin_marketcap":"https://coinmarketcap.com/currencies/ethereum/","google_finance":"https://www.google.com/finance/quote/ETH-USD"},"stock_status":"active","bid":"2633.09","ask":"2633.09","last":"2633.09"}]
async def get_positions():
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_ENDPOINT}/getPositions",
            headers={"authorization": API_KEY},
            params={"strategy_id": STRATEGY_ID},
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            data = await response.json()
            if not data["response"] or not isinstance(data["response"], list):
                raise ValueError("Positions response is invalid")
            return data["response"]

# deleteAllOpenOrders
# Example Response: {"status":"success","message":"All open orders deleted"}
async def delete_all_open_orders():
    async with aiohttp.ClientSession() as session:
        # Fetch all orders
        async with session.get(
            f"{API_ENDPOINT}/getOrders",
            headers={"authorization": API_KEY},
            params={"strategy_id": STRATEGY_ID},
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            orders = (await response.json())["response"]
        
        # Delete each order
        for order in orders:
            async with session.post(
                f"{API_ENDPOINT}/deleteOrder",
                headers={"authorization": API_KEY},
                json={"strategy_id": STRATEGY_ID, "order_id": order["order_id"]},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                await response.json()

# newOrder <stock_id> <action> <type> --amount-- --total-- --price-- --stop_price--
# Example Response: {"status":"success","order_id":"ORD123456","message":"Order placed successfully"}
async def new_order(params):
    try:
        order_params = NewOrderParams(**params)
    except ValidationError as e:
        raise ValueError(str(e))
    
    # Additional validation
    if order_params.type in ['limit', 'stop_limit', 'oco'] and order_params.price is None:
        raise ValueError('Price is required for limit orders')
    if order_params.type in ['stop_limit', 'stop_market', 'oco'] and order_params.stop_price is None:
        raise ValueError('Stop price is required for stop orders')
    
    if order_params.action == 'sell':
        if order_params.total:
            raise ValueError('Total is not allowed for sell orders')
        if not order_params.amount:
            raise ValueError('Amount is required for sell orders')
        amount = str(Decimal(order_params.amount))
    elif order_params.action == 'buy':
        if order_params.amount:
            raise ValueError('Amount is not allowed for buy orders')
        if not order_params.total:
            raise ValueError('Total is required for buy orders')
        total = str(Decimal(order_params.total))
    
    data = {
        "strategy_id": STRATEGY_ID,
        "stock_id": order_params.stock_id,
        "action": order_params.action,
        "type": order_params.type,
    }
    if order_params.action == 'sell':
        data["amount"] = amount
    elif order_params.action == 'buy':
        data["total"] = total
    if order_params.price is not None:
        data["price"] = order_params.price
    if order_params.stop_price is not None:
        data["stop_price"] = order_params.stop_price
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_ENDPOINT}/newOrder",
            headers={"authorization": API_KEY},
            json=data,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            await response.json()

# getStocks <[stock_id]>
# Example Response: [{"stock_id":"9ot8fZX7romhU2Q8kV97r","figi_composite":"BBG000N9MNX3","symbol":"TSLA","name":"Tesla, Inc. Common Stock","sector":"Manufacturing","security":"stock","exchange":"NASDAQ","stock":"TSLA","peg":"USD","provider":"polygon","slippage":"0.000000000000000","fee":"0.000000000000000","links":{"finviz":"https://www.finviz.com/quote.ashx?t=TSLA","trading_view":"https://www.tradingview.com/symbols/NASDAQ-TSLA/","yahoo_finance":"https://finance.yahoo.com/quote/TSLA","google_finance":"https://www.google.com/finance/quote/TSLA:NASDAQ"},"stock_status":"active","bid":"217.88","ask":"217.96","last":"217.96"}]
async def get_stocks(stock_ids):
    if not isinstance(stock_ids, list) or not all(isinstance(s, str) for s in stock_ids):
        raise ValueError("stock_ids must be a list of strings")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_ENDPOINT}/getStocks",
            headers={"authorization": API_KEY},
            params={"stock_id": stock_ids},
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            data = await response.json()
            return data["response"]

# Main function
async def rebalance():
    global positions
    
    # Get strategy
    strategy = await get_strategy()
    
    # Get stocks
    stock_ids = [
        f"{position['symbol']}:{'COINBASE' if strategy['type'] == 'cryptocurrency' else 'ALPHAINSIDER' if position['symbol'] == 'USD' else ''}"
        for position in positions
    ]
    stocks = await get_stocks(stock_ids)
    
    # Map positions with stock data
    positions = [
        {
            **position,
            "stock_id": "ubfhvYUsgvMIuJPwr76My",
            "price": "1"
        } if position["symbol"] == "USD" else {
            **position,
            "stock_id": next((stock["stock_id"] for stock in stocks if stock["stock"] == position["symbol"]), None),
            "price": next((stock["last"] for stock in stocks if stock["stock"] == position["symbol"]), None)
        }
        for position in positions
    ]
    
    # Verify all positions have stock_id and price
    if any(not p.get("stock_id") or not p.get("price") for p in positions):
        raise ValueError("Some positions do not have corresponding stocks or prices")
    
    # Calculate total desired value
    total = sum(Decimal(p["amount"]) * Decimal(p["price"]) for p in positions)
    
    # Get strategy value
    strategy_value_data = await get_strategy_value()
    strategy_value = Decimal(strategy_value_data["strategy_value"])
    
    # Cancel all open orders
    await delete_all_open_orders()
    
    # Get current positions
    current_positions = await get_positions()
    current_positions_map = {pos["stock_id"]: pos for pos in current_positions}
    
    # Adjust non-USD positions
    for position in [p for p in positions if p["symbol"] != "USD"]:
        stock = next(s for s in stocks if s["stock_id"] == position["stock_id"])
        price = Decimal(stock["last"])
        
        desired_amount = Decimal(position["amount"])
        target_amount = (desired_amount / total) * strategy_value
        
        current_position = current_positions_map.get(position["stock_id"])
        current_amount = Decimal(current_position["amount"]) if current_position else Decimal(0)
        difference = target_amount - current_amount
        
        if difference > 0:
            total_to_buy = difference * price
            await new_order({
                "stock_id": position["stock_id"],
                "action": "buy",
                "type": "market",
                "total": str(total_to_buy),
            })
            print(f"Bought {difference} {position['symbol']} for {total_to_buy} USD")
        elif difference < 0:
            amount_to_sell = str(-difference)
            await new_order({
                "stock_id": position["stock_id"],
                "action": "sell",
                "type": "market",
                "amount": amount_to_sell,
            })
            print(f"Sold {amount_to_sell} {position['symbol']}")
    
    # Sell positions not in desired positions
    desired_stock_ids = [p["stock_id"] for p in positions]
    for current_position in current_positions:
        if current_position["symbol"] != "USD" and current_position["stock_id"] not in desired_stock_ids:
            await new_order({
                "stock_id": current_position["stock_id"],
                "action": "sell",
                "type": "market",
                "amount": current_position["amount"],
            })
            print(f"Sold all {current_position['symbol']}")
    
    print("Rebalance completed")

# Main execution
async def main():
    start_time = time.perf_counter()
    try:
        await rebalance()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        end_time = time.perf_counter()
        print(f"Time taken: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())