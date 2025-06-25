import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from loguru import logger
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from src.config import settings
from src.analysis.consensus_engine import TradeRecommendation
from src.risk.risk_manager import Position, RiskMetrics


class TelegramReporter:
    def __init__(self):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.chat_id = settings.telegram_chat_id
        self.app = None
        
    async def initialize(self):
        """Initialize the Telegram bot"""
        self.app = Application.builder().token(settings.telegram_bot_token).build()
        
        # Add command handlers
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CommandHandler("status", self._status_command))
        self.app.add_handler(CommandHandler("positions", self._positions_command))
        self.app.add_handler(CommandHandler("risk", self._risk_command))
        self.app.add_handler(CommandHandler("help", self._help_command))
        
        # Start the bot
        await self.app.initialize()
        await self.app.start()
        
    async def send_trade_recommendations(self, recommendations: List[TradeRecommendation]):
        """Send trade recommendations to Telegram"""
        if not recommendations:
            message = "⚠️ **No Trade Recommendations**\\n\\n"
            message += "No high-confidence trading opportunities found for this analysis cycle\\."
            await self._send_message(message)
            return
            
        message = "🎯 **WEEKLY TRADE RECOMMENDATIONS**\\n\\n"
        message += f"_Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}_\\n\\n"
        
        for i, rec in enumerate(recommendations[:3], 1):  # Top 3 recommendations
            emoji = "🟢" if rec.action == "LONG" else "🔴"
            
            message += f"**{i}\\. {emoji} {rec.symbol} \\- {rec.action}**\\n"
            message += f"├ Entry: \\${rec.entry_price:.4f}\\n"
            message += f"├ Target: \\${rec.target_price:.4f} \\({rec.expected_return:.1f}%\\)\\n"
            message += f"├ Stop Loss: \\${rec.stop_loss:.4f}\\n"
            message += f"├ Position Size: {rec.position_size_percent:.1%} of capital\\n"
            message += f"├ Risk/Reward: {rec.risk_reward_ratio:.2f}\\n"
            message += f"├ Confidence: {rec.confidence:.1%}\\n"
            message += f"└ Reasoning: _{self._escape_markdown(rec.consensus_reasoning[:200])}_\\n\\n"
            
            if rec.risk_factors:
                message += f"⚠️ **Risk Factors:**\\n"
                for risk in rec.risk_factors[:3]:
                    message += f"  • {self._escape_markdown(risk)}\\n"
                message += "\\n"
                
        message += "\\n💡 **Trading Tips:**\\n"
        message += "• Use proper position sizing\\n"
        message += "• Set stop losses immediately\\n"
        message += "• Monitor positions regularly\\n"
        message += "• Never risk more than you can afford to lose"
        
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton("View Positions", callback_data="positions"),
                InlineKeyboardButton("Risk Report", callback_data="risk")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message(message, reply_markup=reply_markup)
        
    async def send_position_update(self, position: Position, event: str):
        """Send position update notification"""
        emoji = "✅" if event == "OPENED" else "❌" if event == "STOP_LOSS" else "💰"
        action_emoji = "🟢" if position.side == "LONG" else "🔴"
        
        message = f"{emoji} **POSITION {event}**\\n\\n"
        message += f"{action_emoji} **{position.symbol} \\- {position.side}**\\n"
        message += f"├ Entry: \\${position.entry_price:.4f}\\n"
        message += f"├ Exit: \\${position.current_price:.4f}\\n"
        message += f"├ PnL: {position.pnl_percentage:.2%} \\(\\${position.pnl:.2f}\\)\\n"
        message += f"└ Duration: {(datetime.now() - position.entry_time).total_seconds() / 3600:.1f} hours"
        
        await self._send_message(message)
        
    async def send_risk_alert(self, alert_type: str, details: str):
        """Send risk management alert"""
        message = f"🚨 **RISK ALERT: {alert_type}**\\n\\n"
        message += self._escape_markdown(details)
        
        await self._send_message(message)
        
    async def send_daily_summary(self, positions: List[Position], risk_metrics: RiskMetrics):
        """Send daily performance summary"""
        total_pnl = sum(p.pnl for p in positions)
        total_pnl_pct = sum(p.pnl_percentage for p in positions) / len(positions) if positions else 0
        
        message = "📊 **DAILY SUMMARY**\\n\\n"
        message += f"_Date: {datetime.now().strftime('%Y-%m-%d')}_\\n\\n"
        
        message += "**Portfolio Performance:**\\n"
        message += f"├ Open Positions: {len(positions)}\\n"
        message += f"├ Total PnL: \\${total_pnl:.2f} \\({total_pnl_pct:.2%}\\)\\n"
        message += f"├ Total Exposure: \\${risk_metrics.total_exposure:.2f}\\n"
        message += f"└ Sharpe Ratio: {risk_metrics.sharpe_ratio:.2f}\\n\\n"
        
        message += "**Risk Metrics:**\\n"
        message += f"├ Current Drawdown: {risk_metrics.current_drawdown:.2%}\\n"
        message += f"├ Max Drawdown: {risk_metrics.max_drawdown:.2%}\\n"
        message += f"├ Portfolio VaR \\(95%\\): {risk_metrics.portfolio_var:.2%}\\n"
        message += f"└ Correlation Risk: {risk_metrics.correlation_risk:.2f}\\n\\n"
        
        if positions:
            message += "**Active Positions:**\\n"
            for p in positions:
                emoji = "🟢" if p.side == "LONG" else "🔴"
                profit_emoji = "📈" if p.pnl_percentage > 0 else "📉"
                message += f"{emoji} {p.symbol}: {profit_emoji} {p.pnl_percentage:.2%}\\n"
                
        await self._send_message(message)
        
        # Send performance chart
        if len(positions) > 0:
            chart = await self._generate_performance_chart(positions)
            if chart:
                await self._send_photo(chart, "Performance Chart")
                
    async def _generate_performance_chart(self, positions: List[Position]) -> Optional[bytes]:
        """Generate performance chart"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
            
            # PnL over time
            times = [p.entry_time for p in positions]
            pnls = [p.pnl_percentage * 100 for p in positions]
            
            ax1.plot(times, pnls, 'b-', marker='o')
            ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5)
            ax1.set_title('Position PnL %')
            ax1.set_ylabel('PnL %')
            ax1.grid(True, alpha=0.3)
            
            # Position sizes
            symbols = [p.symbol for p in positions]
            sizes = [p.size for p in positions]
            colors = ['green' if p.side == 'LONG' else 'red' for p in positions]
            
            ax2.bar(range(len(symbols)), sizes, color=colors, alpha=0.7)
            ax2.set_xticks(range(len(symbols)))
            ax2.set_xticklabels(symbols, rotation=45)
            ax2.set_title('Position Sizes')
            ax2.set_ylabel('Size (USDT)')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            buf.seek(0)
            plt.close()
            
            return buf.read()
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None
            
    async def _send_message(self, text: str, reply_markup=None):
        """Send message to Telegram"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            
    async def _send_photo(self, photo_bytes: bytes, caption: str):
        """Send photo to Telegram"""
        try:
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo_bytes,
                caption=caption
            )
        except Exception as e:
            logger.error(f"Error sending Telegram photo: {e}")
            
    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for Markdown V2"""
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text
        
    # Command handlers
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "Welcome to Crypto Trading Bot! 🚀\\n\\n"
            "I'll send you trade recommendations and updates\\. "
            "Use /help to see available commands\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        await update.message.reply_text("Bot is running and monitoring markets\\. 📊")
        
    async def _positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        # This would connect to the actual position manager
        await update.message.reply_text("Fetching current positions\\.\\.\\.")
        
    async def _risk_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk command"""
        # This would connect to the actual risk manager
        await update.message.reply_text("Generating risk report\\.\\.\\.")
        
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
**Available Commands:**

/start \\- Start the bot
/status \\- Check bot status
/positions \\- View current positions
/risk \\- View risk metrics
/help \\- Show this help message

**Features:**
• Weekly trade recommendations
• Real\\-time position updates  
• Risk management alerts
• Daily performance summaries
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN_V2)