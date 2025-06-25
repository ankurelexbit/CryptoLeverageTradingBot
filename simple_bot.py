#!/usr/bin/env python3
"""
Simplified crypto bot for on-demand analysis.
No scheduling, no persistent storage, just pure analysis.
"""

import asyncio
from typing import List, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.config import settings
from src.api import BinanceClient
from src.analysis.technical_analyzer import TechnicalAnalyzer
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.analysis.ai_analyzer import AIAnalyzer
from src.analysis.consensus_engine import ConsensusEngine
from src.risk.risk_manager import RiskManager
from src.telegram.telegram_bot import TelegramReporter


class SimpleCryptoBot:
    """Simplified bot for on-demand analysis"""
    
    def __init__(self):
        self.binance = BinanceClient()
        self.technical = TechnicalAnalyzer()
        self.sentiment = SentimentAnalyzer()
        self.ai = AIAnalyzer()
        self.consensus = ConsensusEngine()
        self.risk = RiskManager()
        self.telegram = TelegramReporter()
        
    async def analyze(self, symbols: Optional[List[str]] = None):
        """
        Run analysis and send results to Telegram.
        
        Args:
            symbols: Optional list of symbols to analyze. 
                    If None, uses configured symbols.
        """
        # Initialize Telegram
        await self.telegram.initialize()
        
        # Use provided symbols or default
        if symbols:
            target_symbols = symbols
        else:
            target_symbols = settings.target_symbols
            
        # Send start message
        await self.telegram._send_message(
            f"🔍 **Starting Analysis**\\n"
            f"Analyzing {len(target_symbols)} symbols for 2X opportunities\\.\\.\\."
        )
        
        # Get valid symbols
        all_futures = await self.binance.get_futures_symbols()
        valid_symbols = [s for s in target_symbols if s.replace('USDT', '/USDT') in all_futures]
        
        # Analyze each symbol
        recommendations = []
        
        for symbol in valid_symbols:
            try:
                # Get market data
                market_data = await self.binance.get_market_sentiment_indicators(symbol)
                if not market_data or market_data.get('price', 0) == 0:
                    continue
                    
                # Technical analysis (simplified - just 1h and 4h)
                signals = []
                for tf in ['1h', '4h']:
                    klines = await self.binance.get_klines(symbol, tf, limit=200)
                    if not klines.empty:
                        signal = self.technical.analyze(klines, symbol, tf)
                        signals.append(signal)
                        
                if not signals:
                    continue
                    
                # Sentiment (simplified)
                sentiment = await self.sentiment.analyze_sentiment(symbol)
                
                # AI Analysis
                gpt4 = await self.ai.analyze_with_gpt4(symbol, signals, sentiment, market_data)
                claude = await self.ai.analyze_with_claude(symbol, signals, sentiment, market_data)
                
                # Consensus
                price = market_data.get('price', 0)
                rec = self.consensus.generate_consensus(
                    gpt4, claude, signals, sentiment, market_data, price
                )
                
                if rec:
                    # Validate
                    valid, reason, size = self.risk.validate_trade(rec, price, 10000)
                    if valid:
                        recommendations.append(rec)
                        
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
                
        # Sort by score
        recommendations.sort(
            key=lambda x: x.confidence * x.expected_return,
            reverse=True
        )
        
        # Send top 3
        await self.telegram.send_trade_recommendations(recommendations[:3])
        
        # Cleanup
        await self.binance.close()
        
        return recommendations[:3]


async def run_analysis(symbols: Optional[List[str]] = None):
    """Convenience function to run analysis"""
    bot = SimpleCryptoBot()
    return await bot.analyze(symbols)


if __name__ == "__main__":
    import sys
    
    # Get symbols from command line
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
        print(f"Analyzing: {', '.join(symbols)}")
        asyncio.run(run_analysis(symbols))
    else:
        print("Analyzing default symbols...")
        asyncio.run(run_analysis())