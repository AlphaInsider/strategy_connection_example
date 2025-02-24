
const axios = require('axios');
const _ = require('lodash');
const math = require('mathjs');
const j = require('joi');

//API
const API_ENDPOINT = 'https://alphainsider.com/api';
const API_KEY = '';
const STRATEGY_ID = '';

//positions
let positions = [
  {
    symbol: 'USD',
    amount: '1000'
  },
  {
    symbol: 'BTC',
    amount: '0.1'
  }
];

//Main execution
Promise.resolve()
.then(async () => {
  console.time('timer');
  return rebalance();
})
.then((result) => {
  console.log(result);
  console.timeEnd('timer');
  console.log('Done!');
})
.catch((error) => {
  console.log('Error:', error);
  console.timeEnd('timer');
})
.finally(() => {
  process.exit(0);
});

//Main function

//rebalance
let rebalance = async () => {
  // Get strategy
  let strategy = await getStrategy();
  
  // Get broker stocks
  let stocks = await getStocks({
    stock_id: _.map(positions, (position) =>
      position.symbol + ':' + ((strategy.type === 'cryptocurrency') ? 'COINBASE' : (position.symbol === 'USD') ? 'ALPHAINSIDER' : '')
    ),
  });
  
  // Map positions with broker stocks
  positions = _.map(positions, (position) => {
    let stock = _.find(stocks, (stock) => stock.stock === position.symbol);
    if(position.symbol === 'USD') return {...position, stock_id: 'ubfhvYUsgvMIuJPwr76My', price: '1'}
    return {
      ...position,
      stock_id: stock ? stock.stock_id : null,
      price: stock ? stock.last : null,
    };
  });
  
  // Verify all positions have stock_id and price
  if (_.some(positions, (position) => !position.stock_id || !position.price)) {
    throw new Error('Some positions do not have corresponding stocks or prices');
  }
  
  // Calculate total desired value
  let total = math.bignumber(0);
  for (let position of positions) {
    let positionValue = math.evaluate('bignumber(a) * bignumber(b)', {
      a: position.amount,
      b: position.price
    }).toString();
    total = math.evaluate('bignumber(a) + bignumber(b)', {
      a: total,
      b: positionValue
    }).toString();
  }
  
  // Get strategy value
  let strategyValue = await getStrategyValue();
  strategyValue = math.bignumber(strategyValue.strategy_value).toString();
  
  // Cancel all open orders
  await deleteAllOpenOrders();
  
  // Get current positions
  let currentPositions = await getPositions();
  let currentPositionsMap = _.keyBy(currentPositions, 'stock_id');
  
  // Adjust non-USD positions
  for (let position of positions.filter((p) => p.symbol !== 'USD')) {
    let stock = _.find(stocks, {stock_id: position.stock_id});
    let price = math.bignumber(stock.last);
    
    let desired_amount = math.bignumber(position.amount);
    let target_amount = math.evaluate('(bignumber(a) / bignumber(b)) * bignumber(c)', {
      a: desired_amount,
      b: total,
      c: strategyValue
    }).toString();
    
    let current_position = currentPositionsMap[position.stock_id];
    let current_amount = current_position ? math.bignumber(current_position.amount) : math.bignumber(0);
    let difference = math.evaluate('bignumber(a) - bignumber(b)', {
      a: target_amount,
      b: current_amount
    }).toString();
    
    if (math.compare(difference, 0) > 0) {
      // Buy the difference
      let total = math.evaluate('bignumber(a) * bignumber(b)', {
        a: difference,
        b: price
      }).toString();
      await newOrder({
        stock_id: position.stock_id,
        action: 'buy',
        type: 'market',
        total: total,
      });
      console.log(`Bought ${difference} ${position.symbol} for ${total} USD`);
    }
    else if (math.compare(difference, 0) < 0) {
      // Sell the difference
      let amount = math.abs(difference).toString();
      await newOrder({
        stock_id: position.stock_id,
        action: 'sell',
        type: 'market',
        amount: amount,
      });
      console.log(`Sold ${amount} ${position.symbol}`);
    }
  }
  
  // Sell positions not in desired positions
  let desired_stock_ids = _.map(positions, 'stock_id');
  for (let current_position of currentPositions) {
    if (current_position.symbol !== 'USD' && !desired_stock_ids.includes(current_position.stock_id)) {
      await newOrder({
        stock_id: current_position.stock_id,
        action: 'sell',
        type: 'market',
        amount: current_position.amount,
      });
      console.log(`Sold all ${current_position.symbol}`);
    }
  }
  
  console.log('Rebalance completed');
};

//Helper functions

//getStrategy
//Example Response: {"strategy_id":"YdNf91nP-Q-YB39RwtlHQ","product_id":"yvtLPHMNML3th6csjO_bV","user_id":"user_1","type":"cryptocurrency","private":false,"name":"vdsvdsvds","description":"","updated_at":"2024-10-07T15:05:09.124Z","created_at":"2024-10-07T15:05:09.124Z","price":0,"subscriber_count":"0","timeframes":[{"timeframe":"week","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"year","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"day","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"month","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"},{"timeframe":"five_year","rank_performance":"4","rank_popular":"4","rank_trending":"5","rank_top":"5","max_drawdown":"0.000000000000000","past_value":"1.000000000000000"}]}
let getStrategy = async () => {
  return axios({
    method: 'GET',
    responseType: 'json',
    url: API_ENDPOINT+'/getStrategies',
    maxRedirects: 5,
    timeout: 5000,
    headers: {
      authorization: API_KEY
    },
    params: {
      strategy_id: [STRATEGY_ID]
    }
  })
  .then((result) => result.data.response)
  .then((data) => j.attempt(data, j.array().min(1).required())[0]);
};

//getStrategyValue
//Example Response: {"strategy_id":"PKw1UvPIoGMARkXTXzYk6","strategy_value":"1.00000000000000000"}
let getStrategyValue = async () => {
  return axios({
    method: 'GET',
    responseType: 'json',
    url: API_ENDPOINT+'/getStrategyValues',
    maxRedirects: 5,
    timeout: 5000,
    headers: {
      authorization: API_KEY
    },
    params: {
      strategy_id: [STRATEGY_ID]
    }
  })
  .then((result) => result.data.response)
  .then((data) => j.attempt(data, j.array().min(1).required())[0]);
};

//trades
//getPositions
//Example Response: [{"position_id":"PAiBXHzE10Fa4ioITCXbX","strategy_id":"7Wy5AzIKY9bCmkIqjcLSg","type":"liability","price":"1.000000000000000","amount":"-0.932626292686600","total":"-0.932626292686600","updated_at":"2024-07-18T20:14:44.660Z","created_at":"2024-07-18T20:14:44.660Z","stock_id":"ubfhvYUsgvMIuJPwr76My","figi_composite":null,"symbol":"USD","name":"US Dollar","sector":"Unallocated","security":"","exchange":"ALPHAINSIDER","stock":"USD","peg":"USD","provider":"alphainsider","slippage":"0.000000000000000","fee":"0.000000000000000","links":{},"stock_status":"active","bid":"1.000000000000000","ask":"1.000000000000000","last":"1.000000000000000"},{"position_id":"XoLx1OyDdRBr_yq4JHJdB","strategy_id":"7Wy5AzIKY9bCmkIqjcLSg","type":"asset","price":"2996.940000000000000","amount":"0.000647643919923","total":"1.940949969374036","updated_at":"2024-07-18T20:14:44.660Z","created_at":"2024-05-08T19:51:06.230Z","stock_id":"v3lhjrwEhNuAOxPT29oxO","figi_composite":null,"symbol":"ETH-USD","name":"Ethereum","sector":"Cryptocurrencies","security":"cryptocurrency","exchange":"COINBASE","stock":"ETH","peg":"USD","provider":"coinbase","slippage":"0.000000000000000","fee":"0.002500000000000","links":{"trading_view":"https://www.tradingview.com/symbols/ETHUSD/?exchange=COINBASE","yahoo_finance":"https://finance.yahoo.com/quote/ETH-USD","coin_marketcap":"https://coinmarketcap.com/currencies/ethereum/","google_finance":"https://www.google.com/finance/quote/ETH-USD"},"stock_status":"active","bid":"2633.09","ask":"2633.09","last":"2633.09"}]
let getPositions = async () => {
  return axios({
    method: 'GET',
    responseType: 'json',
    url: API_ENDPOINT+'/getPositions',
    maxRedirects: 5,
    timeout: 5000,
    headers: {
      authorization: API_KEY
    },
    params: {
      strategy_id: STRATEGY_ID
    }
  })
  .then((result) => result.data.response)
  .then((data) => j.attempt(data, j.array().min(1).required()))
};

//deleteAllOpenOrders
let deleteAllOpenOrders = async () => {
  //get all orders
  let orders = await axios({
    method: 'GET',
    responseType: 'json',
    url: API_ENDPOINT+'/getOrders',
    maxRedirects: 5,
    timeout: 5000,
    headers: {
      authorization: API_KEY
    },
    params: {
      strategy_id: STRATEGY_ID
    }
  })
  .then((result) => result.data.response);
  
  //delete all orders
  for(let order of orders) {
    await axios({
      method: 'POST',
      responseType: 'json',
      url: API_ENDPOINT+'/deleteOrder',
      maxRedirects: 5,
      timeout: 5000,
      headers: {
        authorization: API_KEY
      },
      data: {
        strategy_id: STRATEGY_ID,
        order_id: order.order_id
      }
    })
    .then((result) => result.data.response);
  }
};

//newOrder <stock_id> <action> <type> --amount-- --total-- --price-- --stop_price--
let newOrder = async (params) => {
  //FILTER
  j.assert(params, j.object({
    stock_id: j.string().max(50).invalid('ubfhvYUsgvMIuJPwr76My', 'USD:ALPHAINSIDER').required(),
    action: j.string().valid('buy', 'sell').required(),
    type: j.string().valid('limit', 'stop_limit', 'stop_market', 'market', 'oco').required(),
    amount: j.number().unsafe().greater(0).allow('').optional(),
    total: j.number().unsafe().greater(0).allow('').optional(),
    price: j.number().greater(0).allow('').optional(),
    stop_price: j.number().greater(0).allow('').optional()
  }).required());
  
  //verify price is set for limit orders
  if (['limit', 'stop_limit', 'oco'].includes(params.type)) {
    j.assert(params.price, j.number().required());
  }
  //verify stop price is set for stop orders
  if (['stop_limit', 'stop_market', 'oco'].includes(params.type)) {
    j.assert(params.stop_price, j.number().required());
  }
  //verify and set amount if sell order
  let amount;
  if(params.action === 'sell') {
    if(params.total) throw new Error('Total is not allowed');
    j.assert(params.amount, j.number().unsafe().required());
    amount = math.evaluate('bignumber(a)', {a: params.amount}).toString();
  }
  //verify and set total if buy order
  let total;
  if(params.action === 'buy') {
    if(params.amount) throw new Error('Amount is not allowed');
    j.assert(params.total, j.number().unsafe().required());
    total = math.evaluate('bignumber(a)', {a: params.total}).toString();
  }
  
  //create new order
  await axios({
    method: 'POST',
    responseType: 'json',
    url: API_ENDPOINT+'/newOrder',
    maxRedirects: 5,
    timeout: 5000,
    headers: {
      authorization: API_KEY
    },
    data: {
      strategy_id: STRATEGY_ID,
      stock_id: params.stock_id,
      action: params.action,
      type: params.type,
      amount: amount,
      total: total,
      price: params.price,
      stop_price: params.stop_price
    }
  })
  .then((result) => result.data.response);
};

//getStocks <[stock_id]>
//Example Response: [{"stock_id":"9ot8fZX7romhU2Q8kV97r","figi_composite":"BBG000N9MNX3","symbol":"TSLA","name":"Tesla, Inc. Common Stock","sector":"Manufacturing","security":"stock","exchange":"NASDAQ","stock":"TSLA","peg":"USD","provider":"polygon","slippage":"0.000000000000000","fee":"0.000000000000000","links":{"finviz":"https://www.finviz.com/quote.ashx?t=TSLA","trading_view":"https://www.tradingview.com/symbols/NASDAQ-TSLA/","yahoo_finance":"https://finance.yahoo.com/quote/TSLA","google_finance":"https://www.google.com/finance/quote/TSLA:NASDAQ"},"stock_status":"active","bid":"217.88","ask":"217.96","last":"217.96"}]
let getStocks = async (params) => {
  //FILTER
  j.assert(params, j.object({
    stock_id: j.array().items(j.string().max(50).required()).required()
  }).required());
  
  return axios({
    method: 'GET',
    responseType: 'json',
    url: API_ENDPOINT+'/getStocks',
    maxRedirects: 5,
    timeout: 5000,
    headers: {
      authorization: API_KEY
    },
    params: {
      stock_id: params.stock_id
    }
  })
  .then((result) => result.data.response);
};