import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from loguru import logger
import ccxt.async_support as ccxt
import ssl
from src.config import settings


class BinanceClient:
    def __init__(self):
        self.api_key = settings.binance_api_key
        self.api_secret = settings.binance_api_secret
        self.client = Client(self.api_key, self.api_secret)
        self.async_client = None
        self._initialize_async_client()
        
    def _initialize_async_client(self):
        self.async_client = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future'  # Use futures market
            },
            'session': None,  # Let ccxt handle session creation
            'verify': False,  # Disable SSL verification for development
        })
        
    async def get_futures_symbols(self) -> List[str]:
        """Get all active futures trading symbols on Binance"""
        try:
            markets = await self.async_client.load_markets()
            futures_symbols = [
                symbol for symbol, market in markets.items() 
                if market['futures'] and market['active'] and symbol.endswith('/USDT')
            ]
            return futures_symbols
        except Exception as e:
            logger.error(f"Error fetching futures symbols: {e}")
            return []
            
    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
        """Get historical kline/candlestick data"""
        try:
            # Convert symbol format (e.g., BTCUSDT to BTC/USDT)
            formatted_symbol = symbol.replace('USDT', '/USDT')
            
            ohlcv = await self.async_client.fetch_ohlcv(
                formatted_symbol, 
                interval, 
                limit=limit
            )
            
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return pd.DataFrame()
            
    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book depth for a symbol"""
        try:
            formatted_symbol = symbol.replace('USDT', '/USDT')
            order_book = await self.async_client.fetch_order_book(
                formatted_symbol, 
                limit=limit
            )
            
            return {
                'bids': order_book['bids'][:limit],
                'asks': order_book['asks'][:limit],
                'timestamp': order_book['timestamp'],
                'bid_volume': sum([bid[1] for bid in order_book['bids'][:limit]]),
                'ask_volume': sum([ask[1] for ask in order_book['asks'][:limit]]),
                'spread': order_book['asks'][0][0] - order_book['bids'][0][0] if order_book['bids'] and order_book['asks'] else 0
            }
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            return {}
            
    async def get_24hr_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker statistics"""
        try:
            formatted_symbol = symbol.replace('USDT', '/USDT')
            ticker = await self.async_client.fetch_ticker(formatted_symbol)
            
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'volume': ticker['baseVolume'],
                'quote_volume': ticker['quoteVolume'],
                'price_change_percent': ticker['percentage'],
                'high': ticker['high'],
                'low': ticker['low'],
                'bid': ticker['bid'],
                'ask': ticker['ask']
            }
        except Exception as e:
            logger.error(f"Error fetching 24hr ticker for {symbol}: {e}")
            return {}
            
    async def get_funding_rate(self, symbol: str) -> Dict:
        """Get funding rate for futures"""
        try:
            formatted_symbol = symbol.replace('USDT', '/USDT')
            funding_rate = await self.async_client.fetch_funding_rate(formatted_symbol)
            
            return {
                'symbol': symbol,
                'funding_rate': funding_rate['fundingRate'],
                'funding_timestamp': funding_rate['fundingDatetime'],
                'next_funding_time': funding_rate['nextFundingDatetime']
            }
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return {}
            
    async def get_open_interest(self, symbol: str) -> Dict:
        """Get open interest for futures"""
        try:
            response = self.client.futures_open_interest(symbol=symbol)
            return {
                'symbol': symbol,
                'open_interest': float(response['openInterest']),
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return {}
            
    async def get_liquidations(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent liquidations"""
        try:
            response = self.client.futures_liquidation_orders(
                symbol=symbol,
                limit=limit
            )
            return [{
                'symbol': liq['symbol'],
                'side': liq['side'],
                'price': float(liq['price']),
                'quantity': float(liq['origQty']),
                'time': pd.to_datetime(liq['time'], unit='ms')
            } for liq in response]
        except Exception as e:
            logger.error(f"Error fetching liquidations for {symbol}: {e}")
            return []
            
    async def get_market_sentiment_indicators(self, symbol: str) -> Dict:
        """Aggregate market sentiment indicators"""
        try:
            # Fetch multiple data points concurrently
            tasks = [
                self.get_24hr_ticker(symbol),
                self.get_funding_rate(symbol),
                self.get_open_interest(symbol),
                self.get_order_book(symbol)
            ]
            
            ticker, funding, open_interest, order_book = await asyncio.gather(*tasks)
            
            # Calculate additional sentiment metrics
            sentiment_data = {
                'symbol': symbol,
                'price': ticker.get('price', 0),
                'volume_24h': ticker.get('volume', 0),
                'price_change_24h': ticker.get('price_change_percent', 0),
                'funding_rate': funding.get('funding_rate', 0),
                'open_interest': open_interest.get('open_interest', 0),
                'bid_ask_spread': order_book.get('spread', 0),
                'order_book_imbalance': (
                    (order_book.get('bid_volume', 0) - order_book.get('ask_volume', 0)) / 
                    (order_book.get('bid_volume', 1) + order_book.get('ask_volume', 1))
                ) if order_book else 0,
                'timestamp': datetime.now()
            }
            
            return sentiment_data
        except Exception as e:
            logger.error(f"Error getting market sentiment for {symbol}: {e}")
            return {}
            
    async def close(self):
        """Close async client connection"""
        if self.async_client:
            await self.async_client.close()