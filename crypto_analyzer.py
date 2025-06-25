"""
Simple importable module for crypto analysis.

Usage:
    from crypto_analyzer import analyze_crypto
    
    # Analyze default symbols
    results = analyze_crypto()
    
    # Analyze specific symbols
    results = analyze_crypto(['BTCUSDT', 'ETHUSDT'])
"""

import asyncio
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the simple bot
from simple_bot import SimpleCryptoBot


def analyze_crypto(symbols: Optional[List[str]] = None) -> List[Dict]:
    """
    Analyze cryptocurrencies and send results to Telegram.
    
    This is a synchronous wrapper around the async analysis function.
    
    Args:
        symbols: Optional list of symbols to analyze (e.g., ['BTCUSDT', 'ETHUSDT'])
                If None, analyzes default configured symbols
    
    Returns:
        List of trade recommendations (top 3)
        
    Example:
        >>> results = analyze_crypto(['BTCUSDT', 'ETHUSDT'])
        >>> for rec in results:
        ...     print(f"{rec.symbol}: {rec.action} at ${rec.entry_price}")
    """
    # Create new event loop if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run analysis
    bot = SimpleCryptoBot()
    recommendations = loop.run_until_complete(bot.analyze(symbols))
    
    # Convert to dict for easier use
    results = []
    for rec in recommendations:
        results.append({
            'symbol': rec.symbol,
            'action': rec.action,
            'confidence': rec.confidence,
            'entry_price': rec.entry_price,
            'target_price': rec.target_price,
            'stop_loss': rec.stop_loss,
            'expected_return': rec.expected_return,
            'risk_reward_ratio': rec.risk_reward_ratio,
            'position_size_percent': rec.position_size_percent,
            'reasoning': rec.consensus_reasoning,
            'risk_factors': rec.risk_factors
        })
    
    return results


# Async version
async def analyze_crypto_async(symbols: Optional[List[str]] = None) -> List[Dict]:
    """
    Async version of analyze_crypto.
    
    Use this if you're already in an async context.
    """
    bot = SimpleCryptoBot()
    recommendations = await bot.analyze(symbols)
    
    # Convert to dict
    results = []
    for rec in recommendations:
        results.append({
            'symbol': rec.symbol,
            'action': rec.action,
            'confidence': rec.confidence,
            'entry_price': rec.entry_price,
            'target_price': rec.target_price,
            'stop_loss': rec.stop_loss,
            'expected_return': rec.expected_return,
            'risk_reward_ratio': rec.risk_reward_ratio,
            'position_size_percent': rec.position_size_percent,
            'reasoning': rec.consensus_reasoning,
            'risk_factors': rec.risk_factors
        })
    
    return results


# Quick test function
def test_analysis():
    """Test the analysis with a single symbol"""
    print("Testing analysis with BTCUSDT...")
    results = analyze_crypto(['BTCUSDT'])
    
    if results:
        print(f"\nFound {len(results)} recommendations:")
        for rec in results:
            print(f"\n{rec['symbol']} - {rec['action']}")
            print(f"  Entry: ${rec['entry_price']:,.2f}")
            print(f"  Target: ${rec['target_price']:,.2f} ({rec['expected_return']:.1f}%)")
            print(f"  Stop Loss: ${rec['stop_loss']:,.2f}")
            print(f"  Confidence: {rec['confidence']:.1%}")
    else:
        print("No recommendations found.")


if __name__ == "__main__":
    # Run test when module is executed directly
    test_analysis()