import asyncio
from typing import List, Dict
from datetime import datetime, timedelta
import schedule
from loguru import logger
import sys

from src.config import settings
from src.api import BinanceClient
from src.analysis.technical_analyzer import TechnicalAnalyzer
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.analysis.ai_analyzer import AIAnalyzer
from src.analysis.consensus_engine import ConsensusEngine
from src.risk.risk_manager import RiskManager
from src.telegram.telegram_bot import TelegramReporter


class CryptoTradingBot:
    def __init__(self):
        # Remove file logging, keep only console
        logger.remove()
        logger.add(sys.stdout, level="INFO")
        logger.info("Initializing Crypto Trading Bot")
        
        self.binance_client = BinanceClient()
        self.technical_analyzer = TechnicalAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.ai_analyzer = AIAnalyzer()
        self.consensus_engine = ConsensusEngine()
        self.risk_manager = RiskManager()
        self.telegram_reporter = TelegramReporter()
        
        self.account_balance = 10000  # Default balance, should be fetched from exchange
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing bot components")
        await self.telegram_reporter.initialize()
        await self.telegram_reporter._send_message(
            "🚀 **Crypto Trading Bot Started**\\n\\n"
            "Bot is now monitoring markets for 2X weekly opportunities\\!"
        )
        
    async def analyze_symbol(self, symbol: str) -> Dict:
        """Perform complete analysis for a single symbol"""
        logger.info(f"Analyzing {symbol}")
        
        try:
            # Fetch market data
            market_data = await self.binance_client.get_market_sentiment_indicators(symbol)
            
            # Technical analysis on multiple timeframes
            technical_signals = []
            for timeframe in settings.technical_timeframes:
                klines = await self.binance_client.get_klines(symbol, timeframe)
                if not klines.empty:
                    signal = self.technical_analyzer.analyze(klines, symbol, timeframe)
                    technical_signals.append(signal)
                    
            # Sentiment analysis
            sentiment_data = await self.sentiment_analyzer.analyze_sentiment(symbol)
            
            # AI analysis
            gpt4_analysis = await self.ai_analyzer.analyze_with_gpt4(
                symbol, technical_signals, sentiment_data, market_data
            )
            
            claude_analysis = await self.ai_analyzer.analyze_with_claude(
                symbol, technical_signals, sentiment_data, market_data
            )
            
            # Generate consensus
            current_price = market_data.get('price', 0)
            recommendation = self.consensus_engine.generate_consensus(
                gpt4_analysis, claude_analysis, technical_signals,
                sentiment_data, market_data, current_price
            )
            
            return {
                'symbol': symbol,
                'recommendation': recommendation,
                'market_data': market_data,
                'technical_signals': technical_signals,
                'sentiment_data': sentiment_data,
                'gpt4_analysis': gpt4_analysis,
                'claude_analysis': claude_analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
            
    async def run_analysis_cycle(self):
        """Run complete analysis cycle for all symbols"""
        logger.info("Starting analysis cycle")
        
        # Get active futures symbols
        all_symbols = await self.binance_client.get_futures_symbols()
        
        # Filter to target symbols
        symbols_to_analyze = [s for s in settings.target_symbols if s.replace('USDT', '/USDT') in all_symbols]
        
        logger.info(f"Analyzing {len(symbols_to_analyze)} symbols")
        
        # Analyze all symbols concurrently
        tasks = [self.analyze_symbol(symbol) for symbol in symbols_to_analyze]
        results = await asyncio.gather(*tasks)
        
        # Filter valid results and recommendations
        valid_results = [r for r in results if r and r.get('recommendation')]
        recommendations = [r['recommendation'] for r in valid_results]
        
        # Sort by confidence and expected return
        recommendations.sort(
            key=lambda x: (x.confidence * x.expected_return),
            reverse=True
        )
        
        # Validate trades through risk manager
        validated_trades = []
        for rec in recommendations[:10]:  # Check top 10
            is_valid, reason, position_size = self.risk_manager.validate_trade(
                rec, rec.entry_price, self.account_balance
            )
            
            if is_valid:
                validated_trades.append(rec)
                if len(validated_trades) >= 3:  # Get top 3 trades
                    break
                    
        logger.info(f"Found {len(validated_trades)} valid trade recommendations")
        
        # Send recommendations via Telegram
        await self.telegram_reporter.send_trade_recommendations(validated_trades)
        
        # Store analysis results in memory only
        # self._store_analysis_results(valid_results)  # Disabled - no persistence
        
        return validated_trades
        
    async def monitor_positions(self):
        """Monitor open positions and manage risk"""
        logger.info("Monitoring positions")
        
        # Get current prices for all positions
        price_updates = {}
        for position in self.risk_manager.positions:
            ticker = await self.binance_client.get_24hr_ticker(position.symbol)
            if ticker:
                price_updates[position.symbol] = ticker['price']
                
        # Update positions
        self.risk_manager.update_positions(price_updates)
        
        # Check stop loss and take profit
        positions_to_close = self.risk_manager.check_stop_loss_take_profit()
        
        for position, reason in positions_to_close:
            await self.telegram_reporter.send_position_update(position, reason)
            self.risk_manager.close_position(position)
            
        # Apply trailing stops
        self.risk_manager.apply_trailing_stop()
        
        # Check risk metrics
        risk_metrics = self.risk_manager.get_risk_metrics()
        
        # Send alerts if needed
        if risk_metrics.current_drawdown < -0.1:  # 10% drawdown
            await self.telegram_reporter.send_risk_alert(
                "HIGH DRAWDOWN",
                f"Current drawdown: {risk_metrics.current_drawdown:.2%}"
            )
            
    async def send_daily_summary(self):
        """Send daily performance summary"""
        logger.info("Sending daily summary")
        
        risk_metrics = self.risk_manager.get_risk_metrics()
        await self.telegram_reporter.send_daily_summary(
            self.risk_manager.positions,
            risk_metrics
        )
        
    def _store_analysis_results(self, results: List[Dict]):
        """Store analysis results for future reference"""
        # In production, implement database storage
        # For now, just log summary
        for result in results:
            if result['recommendation']:
                rec = result['recommendation']
                logger.info(
                    f"Recommendation: {rec.symbol} {rec.action} "
                    f"Confidence: {rec.confidence:.2%} "
                    f"Expected Return: {rec.expected_return:.1f}%"
                )
                
    async def schedule_jobs(self):
        """Schedule periodic jobs"""
        # Run analysis every 4 hours
        schedule.every(settings.analysis_interval_hours).hours.do(
            lambda: asyncio.create_task(self.run_analysis_cycle())
        )
        
        # Monitor positions every 5 minutes
        schedule.every(5).minutes.do(
            lambda: asyncio.create_task(self.monitor_positions())
        )
        
        # Send daily summary at 00:00 UTC
        schedule.every().day.at("00:00").do(
            lambda: asyncio.create_task(self.send_daily_summary())
        )
        
        # Run the scheduler
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
            
    async def run(self):
        """Main bot execution"""
        try:
            await self.initialize()
            
            # Run initial analysis
            await self.run_analysis_cycle()
            
            # Start scheduled jobs
            await self.schedule_jobs()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
            await self.telegram_reporter.send_risk_alert("BOT ERROR", str(e))
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources")
        await self.binance_client.close()
        await self.telegram_reporter._send_message("🛑 **Bot Stopped**")
        

async def main():
    """Main entry point"""
    bot = CryptoTradingBot()
    await bot.run()


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())