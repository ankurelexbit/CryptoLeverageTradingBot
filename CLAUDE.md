# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cryptocurrency leverage trading bot project. The repository is currently in its initial setup phase with minimal code structure.

## Current Repository State

The repository contains only basic configuration files:
- `.claude/settings.local.json` - Claude Code permissions configuration

## Development Setup

Since this is a new project, the specific technology stack and development commands are not yet established. When setting up the project, consider:

1. **Language/Framework Selection**: Typically trading bots are built with Python (for data analysis and ML capabilities) or JavaScript/TypeScript (for real-time operations)

2. **Key Components to Implement**:
   - Exchange API integrations (Binance, Coinbase, etc.)
   - Market data processing and analysis
   - Risk management and position sizing
   - Order execution and monitoring
   - Configuration management for trading parameters
   - Logging and monitoring systems
   - Backtesting framework

3. **Security Considerations**:
   - API keys and secrets management (use environment variables)
   - Input validation for trading parameters
   - Rate limiting for exchange API calls
   - Secure storage of trading history and logs

## Architecture Recommendations

When developing the bot, structure the codebase with:
- **Config Management**: Centralized configuration for different exchanges and trading strategies
- **Data Layer**: Market data ingestion, processing, and storage
- **Strategy Engine**: Trading logic and signal generation
- **Execution Layer**: Order placement and portfolio management
- **Monitoring**: Real-time dashboards and alerting

## Important Notes

- **Risk Management**: Always implement proper risk controls before live trading
- **Paper Trading**: Test all strategies in simulation mode first
- **Exchange Compliance**: Ensure compliance with exchange rate limits and terms of service
- **Error Handling**: Implement robust error handling for network issues and API failures

## Development Workflow

Once the project structure is established, this file should be updated with:
- Build and test commands
- Environment setup instructions
- API configuration steps
- Deployment procedures