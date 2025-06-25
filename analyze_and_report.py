#!/usr/bin/env python3
"""
Simple analysis and report function for crypto trading bot.
Run this script to perform analysis and get results on Telegram.
"""

import asyncio
import sys
from datetime import datetime
from loguru import logger
from typing import List

from src.config import settings
from src.api import BinanceClient
from src.analysis.technical_analyzer import TechnicalAnalyzer
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.analysis.ai_analyzer import AIAnalyzer
from src.analysis.consensus_engine import ConsensusEngine
from src.risk.risk_manager import RiskManager
from src.telegram.telegram_bot import TelegramReporter


async def analyze_and_report():
    """
    Perform market analysis and send trade recommendations to Telegram.
    This is a simplified version that runs once and exits.
    """
    
    # Setup logging
    logger.remove()  # Remove default handler
    logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    
    logger.info("🚀 Starting Crypto Analysis...")
    
    # Initialize components
    binance_client = BinanceClient()
    technical_analyzer = TechnicalAnalyzer()
    sentiment_analyzer = SentimentAnalyzer()
    ai_analyzer = AIAnalyzer()
    consensus_engine = ConsensusEngine()
    risk_manager = RiskManager()
    telegram_reporter = TelegramReporter()
    
    try:
        # Initialize Telegram bot
        await telegram_reporter.initialize()
        
        # Send start message
        await telegram_reporter._send_message(
            "🔍 **Starting Market Analysis**\\n\\n"
            f"_Analyzing top crypto futures for 2X opportunities\\.\\.\\._\\n"
            f"_Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}_"
        )
        
        # Get symbols to analyze
        logger.info("Fetching active futures symbols...")
        all_symbols = await binance_client.get_futures_symbols()
        symbols_to_analyze = [s for s in settings.target_symbols if s.replace('USDT', '/USDT') in all_symbols]
        
        logger.info(f"Found {len(symbols_to_analyze)} symbols to analyze")
        
        # Store all analysis results
        all_recommendations = []
        
        # Analyze each symbol
        for i, symbol in enumerate(symbols_to_analyze):
            logger.info(f"Analyzing {symbol} ({i+1}/{len(symbols_to_analyze)})...")
            
            try:
                # Get market data
                market_data = await binance_client.get_market_sentiment_indicators(symbol)
                if not market_data or market_data.get('price', 0) == 0:
                    continue
                
                # Technical analysis
                technical_signals = []
                for timeframe in settings.technical_timeframes[:2]:  # Use only 2 timeframes for speed
                    klines = await binance_client.get_klines(symbol, timeframe, limit=200)
                    if not klines.empty:
                        signal = technical_analyzer.analyze(klines, symbol, timeframe)
                        technical_signals.append(signal)
                
                if not technical_signals:
                    continue
                
                # Sentiment analysis (simplified)
                logger.info(f"Analyzing sentiment for {symbol}...")
                sentiment_data = await sentiment_analyzer.analyze_sentiment(symbol)
                
                # AI analysis
                logger.info(f"Running AI analysis for {symbol}...")
                
                # GPT-4 Analysis
                gpt4_analysis = await ai_analyzer.analyze_with_gpt4(
                    symbol, technical_signals, sentiment_data, market_data
                )
                
                # Claude Analysis
                claude_analysis = await ai_analyzer.analyze_with_claude(
                    symbol, technical_signals, sentiment_data, market_data
                )
                
                # Generate consensus
                current_price = market_data.get('price', 0)
                recommendation = consensus_engine.generate_consensus(
                    gpt4_analysis, claude_analysis, technical_signals,
                    sentiment_data, market_data, current_price
                )
                
                if recommendation:
                    # Validate through risk manager
                    is_valid, reason, position_size = risk_manager.validate_trade(
                        recommendation, current_price, risk_manager.account_balance
                    )
                    
                    if is_valid:
                        all_recommendations.append(recommendation)
                        logger.info(f"✅ Valid recommendation for {symbol}: {recommendation.action}")
                    else:
                        logger.info(f"❌ {symbol} rejected: {reason}")
                        
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        # Sort recommendations by confidence * expected return
        all_recommendations.sort(
            key=lambda x: (x.confidence * x.expected_return),
            reverse=True
        )
        
        # Take top 3 recommendations
        top_recommendations = all_recommendations[:3]
        
        logger.info(f"Analysis complete. Found {len(top_recommendations)} recommendations.")
        
        # Send results to Telegram
        await telegram_reporter.send_trade_recommendations(top_recommendations)
        
        # Send summary
        summary_msg = f"📊 **Analysis Summary**\\n\\n"
        summary_msg += f"• Symbols analyzed: {len(symbols_to_analyze)}\\n"
        summary_msg += f"• Valid opportunities: {len(all_recommendations)}\\n"
        summary_msg += f"• Top picks sent: {len(top_recommendations)}\\n"
        summary_msg += f"\\n_Analysis completed successfully\\!_"
        
        await telegram_reporter._send_message(summary_msg)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await telegram_reporter._send_message(
            f"❌ **Analysis Failed**\\n\\n"
            f"Error: {str(e)[:100]}\\.\\.\\."
        )
    finally:
        # Cleanup
        await binance_client.close()
        logger.info("Analysis complete. Exiting.")


async def quick_analysis(symbols: List[str] = None):
    """
    Quick analysis function for specific symbols.
    
    Args:
        symbols: List of symbols to analyze (e.g., ['BTCUSDT', 'ETHUSDT'])
                If None, uses default symbols from settings
    """
    if symbols:
        # Override settings temporarily
        original_symbols = settings.target_symbols
        settings.target_symbols = symbols
        
    try:
        await analyze_and_report()
    finally:
        if symbols:
            settings.target_symbols = original_symbols


if __name__ == "__main__":
    # Check if specific symbols were provided as arguments
    if len(sys.argv) > 1:
        # Usage: python analyze_and_report.py BTCUSDT ETHUSDT SOLUSDT
        symbols = sys.argv[1:]
        logger.info(f"Analyzing specific symbols: {symbols}")
        asyncio.run(quick_analysis(symbols))
    else:
        # Analyze all configured symbols
        asyncio.run(analyze_and_report())