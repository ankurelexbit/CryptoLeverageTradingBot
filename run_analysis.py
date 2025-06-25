#!/usr/bin/env python3
"""
Simple one-shot analysis script.
Run this to analyze markets once and get results on Telegram.

Usage:
    python run_analysis.py                    # Analyze all configured symbols
    python run_analysis.py BTCUSDT ETHUSDT   # Analyze specific symbols
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the analysis function
from analyze_and_report import analyze_and_report, quick_analysis


def main():
    """Main entry point for one-shot analysis"""
    import sys
    
    print("🚀 Crypto Trading Bot - One-Shot Analysis")
    print("-" * 50)
    
    # Check for required environment variables
    required_vars = [
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET', 
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        return
    
    # Run analysis
    if len(sys.argv) > 1:
        # Specific symbols provided
        symbols = sys.argv[1:]
        print(f"Analyzing specific symbols: {', '.join(symbols)}")
        asyncio.run(quick_analysis(symbols))
    else:
        # Analyze all configured symbols
        print("Analyzing all configured symbols...")
        asyncio.run(analyze_and_report())
    
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()