import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import openai
import anthropic
import httpx
import ssl
from loguru import logger
from dataclasses import dataclass, asdict
import asyncio
from src.config import settings
from src.analysis.technical_analyzer import TechnicalSignal
from src.sentiment.sentiment_analyzer import SentimentData


@dataclass
class AIAnalysis:
    model: str
    symbol: str
    recommendation: str  # 'STRONG_BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG_SELL'
    confidence: float  # 0-1
    target_price: float
    stop_loss: float
    take_profit: float
    reasoning: str
    risk_assessment: str
    timeframe: str
    timestamp: datetime


class AIAnalyzer:
    def __init__(self):
        # Create HTTP client with SSL verification disabled for development
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        http_client = httpx.Client(
            verify=False,
            timeout=30.0
        )
        
        self.openai_client = openai.OpenAI(
            api_key=settings.openai_api_key,
            http_client=http_client
        )
        self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        
    async def analyze_with_gpt4(
        self,
        symbol: str,
        technical_signals: List[TechnicalSignal],
        sentiment_data: Dict[str, SentimentData],
        market_data: Dict
    ) -> AIAnalysis:
        """Analyze using GPT-4"""
        try:
            prompt = self._build_analysis_prompt(symbol, technical_signals, sentiment_data, market_data)
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=settings.gpt_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            return AIAnalysis(
                model='gpt-4',
                symbol=symbol,
                recommendation=analysis.get('recommendation', 'NEUTRAL'),
                confidence=float(analysis.get('confidence', 0.5)),
                target_price=float(analysis.get('target_price', 0)),
                stop_loss=float(analysis.get('stop_loss', 0)),
                take_profit=float(analysis.get('take_profit', 0)),
                reasoning=analysis.get('reasoning', ''),
                risk_assessment=analysis.get('risk_assessment', ''),
                timeframe=analysis.get('timeframe', '1 week'),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in GPT-4 analysis for {symbol}: {e}")
            return self._get_default_analysis('gpt-4', symbol)
            
    async def analyze_with_claude(
        self,
        symbol: str,
        technical_signals: List[TechnicalSignal],
        sentiment_data: Dict[str, SentimentData],
        market_data: Dict
    ) -> AIAnalysis:
        """Analyze using Claude"""
        try:
            prompt = self._build_analysis_prompt(symbol, technical_signals, sentiment_data, market_data)
            
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model=settings.claude_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system=self._get_system_prompt(),
                temperature=settings.temperature,
                max_tokens=settings.max_tokens
            )
            
            # Extract JSON from Claude's response
            content = response.content[0].text
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            analysis_json = content[json_start:json_end]
            analysis = json.loads(analysis_json)
            
            return AIAnalysis(
                model='claude',
                symbol=symbol,
                recommendation=analysis.get('recommendation', 'NEUTRAL'),
                confidence=float(analysis.get('confidence', 0.5)),
                target_price=float(analysis.get('target_price', 0)),
                stop_loss=float(analysis.get('stop_loss', 0)),
                take_profit=float(analysis.get('take_profit', 0)),
                reasoning=analysis.get('reasoning', ''),
                risk_assessment=analysis.get('risk_assessment', ''),
                timeframe=analysis.get('timeframe', '1 week'),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in Claude analysis for {symbol}: {e}")
            return self._get_default_analysis('claude', symbol)
            
    def _get_system_prompt(self) -> str:
        """Get system prompt for AI models"""
        return """You are an expert cryptocurrency futures trader and analyst with deep knowledge of technical analysis, market sentiment, and risk management. Your goal is to identify high-probability trades that could potentially yield 2X returns within a week while managing risk appropriately.

Analyze the provided data and return a JSON response with the following structure:
{
    "recommendation": "STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL",
    "confidence": 0.0-1.0,
    "target_price": current_price * 2 for 2X return,
    "stop_loss": price level for risk management,
    "take_profit": price level for profit taking,
    "reasoning": "Detailed explanation of your analysis",
    "risk_assessment": "Assessment of risks and market conditions",
    "timeframe": "Expected timeframe for the trade"
}

Consider:
1. Technical indicators and their confluence
2. Market sentiment from social media and news
3. Order book dynamics and liquidity
4. Funding rates and open interest
5. Overall market conditions
6. Risk/reward ratio

Focus on identifying opportunities with:
- Strong technical setup
- Positive sentiment shift
- Good liquidity
- Reasonable risk levels
- Potential for 2X returns within a week"""

    def _build_analysis_prompt(
        self,
        symbol: str,
        technical_signals: List[TechnicalSignal],
        sentiment_data: Dict[str, SentimentData],
        market_data: Dict
    ) -> str:
        """Build analysis prompt with all data"""
        prompt_parts = [f"Analyze {symbol} for potential 2X weekly return opportunity:\n"]
        
        # Technical Analysis Summary
        prompt_parts.append("\n**TECHNICAL ANALYSIS:**")
        for signal in technical_signals:
            prompt_parts.append(f"- {signal.timeframe}: {signal.signal_type} (strength: {signal.strength:.2f})")
            prompt_parts.append(f"  Reasoning: {signal.reasoning}")
            prompt_parts.append(f"  Key indicators: {json.dumps(signal.indicators, indent=2)}")
            
        # Sentiment Analysis Summary
        prompt_parts.append("\n**SENTIMENT ANALYSIS:**")
        for source, data in sentiment_data.items():
            prompt_parts.append(f"- {source}: Score {data.sentiment_score:.2f} (Volume: {data.volume})")
            prompt_parts.append(f"  Topics: {', '.join(data.key_topics)}")
            
        # Market Data Summary
        prompt_parts.append("\n**MARKET DATA:**")
        prompt_parts.append(f"- Current Price: ${market_data.get('price', 0):.4f}")
        prompt_parts.append(f"- 24h Volume: ${market_data.get('volume_24h', 0):,.0f}")
        prompt_parts.append(f"- 24h Change: {market_data.get('price_change_24h', 0):.2f}%")
        prompt_parts.append(f"- Funding Rate: {market_data.get('funding_rate', 0):.4f}")
        prompt_parts.append(f"- Open Interest: ${market_data.get('open_interest', 0):,.0f}")
        prompt_parts.append(f"- Order Book Imbalance: {market_data.get('order_book_imbalance', 0):.2f}")
        
        prompt_parts.append("\nProvide your analysis and trading recommendation in JSON format.")
        
        return "\n".join(prompt_parts)
        
    def _get_default_analysis(self, model: str, symbol: str) -> AIAnalysis:
        """Return default neutral analysis in case of errors"""
        return AIAnalysis(
            model=model,
            symbol=symbol,
            recommendation='NEUTRAL',
            confidence=0.0,
            target_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            reasoning='Analysis failed due to technical error',
            risk_assessment='Unable to assess risk',
            timeframe='N/A',
            timestamp=datetime.now()
        )