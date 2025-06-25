#!/usr/bin/env python3
"""
Quick start script for crypto analysis.
This is the simplest way to run the analysis.
"""

import os
import ssl
import certifi
from dotenv import load_dotenv
from crypto_analyzer import analyze_crypto

# Disable SSL verification for development
ssl._create_default_https_context = ssl._create_unverified_context

# Load environment variables
load_dotenv()

def main():
    print("🚀 Crypto Bot Quick Start")
    print("=" * 40)
    
    # Check environment
    required = {
        'BINANCE_API_KEY': 'Binance API Key',
        'BINANCE_API_SECRET': 'Binance API Secret',
        'OPENAI_API_KEY': 'OpenAI API Key',
        'ANTHROPIC_API_KEY': 'Anthropic API Key',
        'TELEGRAM_BOT_TOKEN': 'Telegram Bot Token',
        'TELEGRAM_CHAT_ID': 'Telegram Chat ID'
    }
    
    missing = []
    for key, name in required.items():
        if not os.getenv(key):
            missing.append(name)
    
    if missing:
        print("❌ Missing required settings:")
        for item in missing:
            print(f"   - {item}")
        print("\nPlease set these in your .env file")
        return
    
    print("✅ All settings configured")
    print("\nStarting analysis...")
    print("Results will be sent to your Telegram!")
    print("-" * 40)
    
    try:
        # Run analysis for top 5 coins
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
        results = analyze_crypto(symbols)
        
        print(f"\n✅ Analysis complete!")
        print(f"Found {len(results)} trade recommendations")
        print("Check your Telegram for details!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Please check your API keys and internet connection")


if __name__ == "__main__":
    main()