# Usage Guide - Crypto Trading Bot

This bot runs entirely in-memory with no persistent storage. All analysis results are sent directly to Telegram.

## Quick Start

### 1. Setup Environment

Create a `.env` file with your API keys:
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Bot

### Option 1: One-Shot Analysis (Recommended)

Run analysis once and get results on Telegram:

```bash
# Analyze all configured symbols
python run_analysis.py

# Analyze specific symbols
python run_analysis.py BTCUSDT ETHUSDT SOLUSDT
```

### Option 2: Direct Function Call

```python
import asyncio
from analyze_and_report import analyze_and_report

# Run analysis
asyncio.run(analyze_and_report())
```

### Option 3: REST API Server

Start the API server:
```bash
python api_server.py
```

Then trigger analysis via HTTP:
```bash
# Trigger analysis of all symbols
curl -X POST http://localhost:5000/analyze

# Analyze specific symbols
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["BTCUSDT", "ETHUSDT"]}'

# Check status
curl http://localhost:5000/status
```

### Option 4: Continuous Monitoring

Run the full bot with scheduled analysis:
```bash
python main.py
```

This will:
- Run analysis every 4 hours
- Monitor positions every 5 minutes
- Send daily summaries

## What the Bot Does

1. **Fetches Market Data**: Gets real-time futures data from Binance
2. **Technical Analysis**: Calculates indicators like RSI, MACD, Bollinger Bands
3. **Sentiment Analysis**: Analyzes Twitter, Reddit, and news sentiment
4. **AI Analysis**: Both GPT-4 and Claude analyze all data
5. **Cross-Validation**: Validates findings between both AI models
6. **Risk Assessment**: Ensures trades meet risk parameters
7. **Telegram Report**: Sends top 3 trade recommendations

## Telegram Output

The bot sends:
- **Trade Recommendations**: Entry, target (2X), stop loss, position size
- **Confidence Scores**: How confident the AI models are
- **Risk Factors**: Important risks to consider
- **Reasoning**: Why each trade was selected

## No Storage Required

- All data is processed in-memory
- No database or file storage needed
- Results sent directly to Telegram
- Each run is independent

## Customization

Edit `src/config/settings.py` to change:
- Which symbols to analyze
- Risk parameters
- Technical indicators
- AI model settings

## Example Output

```
🎯 WEEKLY TRADE RECOMMENDATIONS

1. 🟢 BTCUSDT - LONG
├ Entry: $43,250.50
├ Target: $86,501.00 (100.0%)
├ Stop Loss: $41,087.50
├ Position Size: 8.5% of capital
├ Risk/Reward: 20.5
├ Confidence: 78.5%
└ Reasoning: Strong AI agreement; Technical analysis: Bullish...

⚠️ Risk Factors:
  • High funding rate may indicate crowded trade
  • Market volatility above average
```

## Tips

- Run during high volume hours for better liquidity analysis
- Check multiple times per week for different opportunities
- Always verify recommendations before trading
- Never risk more than you can afford to lose