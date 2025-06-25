# Crypto Leverage Trading Bot

An advanced cryptocurrency futures trading bot that uses GPT-4 and Claude AI models to identify potential 2X weekly return opportunities on Binance futures.

## Features

- **Dual AI Analysis**: Uses both GPT-4 and Claude for cross-validation
- **Technical Analysis**: Multiple indicators across different timeframes
- **Sentiment Analysis**: Twitter, Reddit, and news sentiment monitoring
- **Risk Management**: Dynamic position sizing, stop-loss management, and portfolio risk controls
- **Telegram Integration**: Real-time trade recommendations and alerts

## Architecture

```
src/
├── api/              # Exchange API integrations
├── analysis/         # Technical and AI analysis modules
├── sentiment/        # Social media sentiment analysis
├── risk/             # Risk management system
├── telegram/         # Telegram bot for notifications
└── config/           # Configuration management
```

## Setup

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Required API Keys**
- Binance API (with futures trading enabled)
- OpenAI API (GPT-4 access)
- Anthropic API (Claude access)
- Twitter API (for sentiment)
- Reddit API (for sentiment)
- Telegram Bot Token

## Usage

Run the bot:
```bash
python main.py
```

## Key Components

### 1. Market Analysis
- Fetches real-time futures data from Binance
- Analyzes order book depth and liquidity
- Monitors funding rates and open interest

### 2. Technical Analysis
- RSI, MACD, Bollinger Bands
- EMA crossovers and trend analysis
- Stochastic oscillator and ADX
- Volume analysis and MFI

### 3. Sentiment Analysis
- Twitter sentiment from crypto influencers
- Reddit sentiment from major crypto subreddits
- News sentiment from leading crypto publications

### 4. AI Analysis
- GPT-4 analyzes all data and provides recommendations
- Claude provides independent analysis for cross-validation
- Consensus engine combines both AI recommendations

### 5. Risk Management
- Position sizing based on Kelly Criterion
- Dynamic stop-loss and trailing stop
- Portfolio correlation analysis
- Maximum drawdown protection

### 6. Trade Execution
- Validates trades against risk parameters
- Monitors positions in real-time
- Automatic stop-loss and take-profit execution
- Performance tracking and reporting

## Configuration

Edit `src/config/settings.py` to customize:
- Trading pairs to monitor
- Risk parameters
- Technical indicator settings
- AI model parameters

## Telegram Commands

- `/start` - Initialize bot
- `/status` - Check bot status
- `/positions` - View open positions
- `/risk` - View risk metrics
- `/help` - Show help

## Safety Features

- Maximum position size limits
- Maximum concurrent positions
- Correlation risk management
- Automatic stop-loss on all trades
- Daily performance summaries

## Disclaimer

This bot is for educational purposes. Cryptocurrency trading involves substantial risk of loss. Always test strategies in simulation mode before live trading. Never invest more than you can afford to lose.

## Development

To add new features:

1. Technical indicators: Modify `src/analysis/technical_analyzer.py`
2. Sentiment sources: Update `src/sentiment/sentiment_analyzer.py`
3. Risk rules: Edit `src/risk/risk_manager.py`
4. AI prompts: Modify `src/analysis/ai_analyzer.py`

## Monitoring

The bot logs all activities to `logs/trading_bot.log` with daily rotation. Monitor this file for:
- Trade recommendations
- Position updates
- Error messages
- Performance metrics

## Future Enhancements

- [ ] Backtesting framework
- [ ] Web dashboard
- [ ] Multiple exchange support
- [ ] Machine learning price prediction
- [ ] Advanced portfolio optimization
- [ ] Automated strategy adjustment