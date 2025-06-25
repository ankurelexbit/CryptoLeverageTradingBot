#!/usr/bin/env python3
"""
Simple REST API server for triggering crypto analysis.
Provides HTTP endpoints to run analysis on-demand.
"""

from flask import Flask, jsonify, request
import asyncio
from datetime import datetime
import threading
from typing import Dict, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import analysis functions
from analyze_and_report import quick_analysis
from src.config import settings

app = Flask(__name__)

# Store analysis status in memory
analysis_status = {
    "is_running": False,
    "last_run": None,
    "last_result": None,
    "error": None
}


def run_async_analysis(symbols: List[str] = None):
    """Run analysis in a separate thread"""
    global analysis_status
    
    try:
        analysis_status["is_running"] = True
        analysis_status["error"] = None
        analysis_status["last_run"] = datetime.now().isoformat()
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run analysis
        loop.run_until_complete(quick_analysis(symbols))
        
        analysis_status["last_result"] = "Analysis completed successfully"
        
    except Exception as e:
        analysis_status["error"] = str(e)
        analysis_status["last_result"] = f"Analysis failed: {str(e)}"
    finally:
        analysis_status["is_running"] = False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/analyze', methods=['POST'])
def trigger_analysis():
    """Trigger market analysis"""
    
    # Check if analysis is already running
    if analysis_status["is_running"]:
        return jsonify({
            "error": "Analysis already in progress",
            "status": analysis_status
        }), 409
    
    # Get optional symbols from request
    data = request.get_json() or {}
    symbols = data.get('symbols', None)
    
    # Validate symbols if provided
    if symbols:
        if not isinstance(symbols, list):
            return jsonify({"error": "Symbols must be a list"}), 400
        
        # Ensure all symbols end with USDT
        symbols = [s.upper() if s.endswith('USDT') else f"{s.upper()}USDT" for s in symbols]
    
    # Run analysis in background thread
    thread = threading.Thread(target=run_async_analysis, args=(symbols,))
    thread.start()
    
    return jsonify({
        "message": "Analysis started",
        "symbols": symbols or settings.target_symbols,
        "status": analysis_status
    })


@app.route('/status', methods=['GET'])
def get_status():
    """Get analysis status"""
    return jsonify({
        "analysis_status": analysis_status,
        "configured_symbols": settings.target_symbols,
        "telegram_configured": bool(os.getenv('TELEGRAM_BOT_TOKEN'))
    })


@app.route('/symbols', methods=['GET'])
def get_symbols():
    """Get list of configured symbols"""
    return jsonify({
        "symbols": settings.target_symbols,
        "count": len(settings.target_symbols)
    })


if __name__ == '__main__':
    print("🌐 Starting Crypto Bot API Server")
    print("=" * 50)
    print("Endpoints:")
    print("  POST /analyze - Trigger analysis")
    print("  GET  /status  - Check analysis status")
    print("  GET  /symbols - Get configured symbols")
    print("  GET  /health  - Health check")
    print("=" * 50)
    
    # Check for required environment variables
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print(f"⚠️  Warning: Missing {', '.join(missing)}")
        print("   Telegram notifications will not work!")
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=False)