from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import numpy as np
from loguru import logger
from src.analysis.ai_analyzer import AIAnalysis
from src.analysis.technical_analyzer import TechnicalSignal
from src.sentiment.sentiment_analyzer import SentimentData


@dataclass
class TradeRecommendation:
    symbol: str
    action: str  # 'LONG', 'SHORT', 'NO_TRADE'
    confidence: float  # 0-1
    entry_price: float
    target_price: float
    stop_loss: float
    position_size_percent: float  # Percentage of capital
    expected_return: float
    risk_reward_ratio: float
    consensus_reasoning: str
    risk_factors: List[str]
    timestamp: datetime


class ConsensusEngine:
    def __init__(self):
        self.min_confidence_threshold = 0.7
        self.min_agreement_score = 0.6
        
    def generate_consensus(
        self,
        gpt4_analysis: AIAnalysis,
        claude_analysis: AIAnalysis,
        technical_signals: List[TechnicalSignal],
        sentiment_data: Dict[str, SentimentData],
        market_data: Dict,
        current_price: float
    ) -> Optional[TradeRecommendation]:
        """Generate consensus trade recommendation from multiple analyses"""
        
        # Calculate agreement score between AI models
        agreement_score = self._calculate_agreement_score(gpt4_analysis, claude_analysis)
        
        # Validate technical signals
        technical_validation = self._validate_technical_signals(technical_signals)
        
        # Validate sentiment
        sentiment_validation = self._validate_sentiment(sentiment_data)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            gpt4_analysis, claude_analysis, agreement_score,
            technical_validation, sentiment_validation
        )
        
        # Determine trade action
        trade_action = self._determine_trade_action(
            gpt4_analysis, claude_analysis, technical_signals, overall_confidence
        )
        
        if trade_action == 'NO_TRADE':
            return None
            
        # Calculate trade parameters
        trade_params = self._calculate_trade_parameters(
            gpt4_analysis, claude_analysis, current_price, trade_action
        )
        
        # Generate consensus reasoning
        reasoning = self._generate_consensus_reasoning(
            gpt4_analysis, claude_analysis, technical_signals,
            sentiment_data, agreement_score
        )
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            gpt4_analysis, claude_analysis, market_data, sentiment_data
        )
        
        return TradeRecommendation(
            symbol=gpt4_analysis.symbol,
            action=trade_action,
            confidence=overall_confidence,
            entry_price=current_price,
            target_price=trade_params['target_price'],
            stop_loss=trade_params['stop_loss'],
            position_size_percent=trade_params['position_size'],
            expected_return=trade_params['expected_return'],
            risk_reward_ratio=trade_params['risk_reward_ratio'],
            consensus_reasoning=reasoning,
            risk_factors=risk_factors,
            timestamp=datetime.now()
        )
        
    def _calculate_agreement_score(self, gpt4: AIAnalysis, claude: AIAnalysis) -> float:
        """Calculate agreement score between AI models"""
        score_components = []
        
        # Recommendation agreement
        rec_map = {
            'STRONG_BUY': 2, 'BUY': 1, 'NEUTRAL': 0, 'SELL': -1, 'STRONG_SELL': -2
        }
        gpt4_score = rec_map.get(gpt4.recommendation, 0)
        claude_score = rec_map.get(claude.recommendation, 0)
        rec_agreement = 1 - (abs(gpt4_score - claude_score) / 4)
        score_components.append(rec_agreement * 0.4)
        
        # Confidence similarity
        conf_diff = abs(gpt4.confidence - claude.confidence)
        conf_agreement = 1 - conf_diff
        score_components.append(conf_agreement * 0.2)
        
        # Price target similarity (within 5% = full agreement)
        if gpt4.target_price > 0 and claude.target_price > 0:
            price_diff = abs(gpt4.target_price - claude.target_price) / gpt4.target_price
            price_agreement = max(0, 1 - (price_diff / 0.05))
            score_components.append(price_agreement * 0.2)
        else:
            score_components.append(0)
            
        # Stop loss similarity
        if gpt4.stop_loss > 0 and claude.stop_loss > 0:
            sl_diff = abs(gpt4.stop_loss - claude.stop_loss) / gpt4.stop_loss
            sl_agreement = max(0, 1 - (sl_diff / 0.05))
            score_components.append(sl_agreement * 0.2)
        else:
            score_components.append(0)
            
        return sum(score_components)
        
    def _validate_technical_signals(self, signals: List[TechnicalSignal]) -> float:
        """Validate technical signals consistency"""
        if not signals:
            return 0.5
            
        buy_count = sum(1 for s in signals if s.signal_type == 'BUY')
        sell_count = sum(1 for s in signals if s.signal_type == 'SELL')
        total_signals = len(signals)
        
        # Calculate directional bias
        if buy_count > sell_count:
            validation_score = buy_count / total_signals
        elif sell_count > buy_count:
            validation_score = sell_count / total_signals
        else:
            validation_score = 0.5
            
        # Factor in signal strength
        avg_strength = np.mean([s.strength for s in signals])
        validation_score *= avg_strength
        
        return validation_score
        
    def _validate_sentiment(self, sentiment_data: Dict[str, SentimentData]) -> float:
        """Validate sentiment consistency"""
        if not sentiment_data:
            return 0.5
            
        # Get aggregate sentiment
        aggregate = sentiment_data.get('aggregate')
        if not aggregate:
            return 0.5
            
        # Convert sentiment score to validation score
        # Strong positive/negative sentiment = high validation
        sentiment_strength = abs(aggregate.sentiment_score)
        
        # Consider volume
        volume_factor = min(aggregate.volume / 100, 1.0)  # Normalize to 0-1
        
        return sentiment_strength * 0.7 + volume_factor * 0.3
        
    def _calculate_overall_confidence(
        self,
        gpt4: AIAnalysis,
        claude: AIAnalysis,
        agreement_score: float,
        technical_validation: float,
        sentiment_validation: float
    ) -> float:
        """Calculate overall confidence score"""
        components = [
            gpt4.confidence * 0.25,
            claude.confidence * 0.25,
            agreement_score * 0.25,
            technical_validation * 0.15,
            sentiment_validation * 0.10
        ]
        
        return sum(components)
        
    def _determine_trade_action(
        self,
        gpt4: AIAnalysis,
        claude: AIAnalysis,
        technical_signals: List[TechnicalSignal],
        confidence: float
    ) -> str:
        """Determine final trade action"""
        if confidence < self.min_confidence_threshold:
            return 'NO_TRADE'
            
        # Map recommendations to scores
        rec_map = {
            'STRONG_BUY': 2, 'BUY': 1, 'NEUTRAL': 0, 'SELL': -1, 'STRONG_SELL': -2
        }
        
        gpt4_score = rec_map.get(gpt4.recommendation, 0)
        claude_score = rec_map.get(claude.recommendation, 0)
        avg_ai_score = (gpt4_score + claude_score) / 2
        
        # Consider technical signals
        tech_buy = sum(1 for s in technical_signals if s.signal_type == 'BUY')
        tech_sell = sum(1 for s in technical_signals if s.signal_type == 'SELL')
        tech_score = (tech_buy - tech_sell) / max(len(technical_signals), 1)
        
        # Combined score
        combined_score = avg_ai_score * 0.7 + tech_score * 0.3
        
        if combined_score >= 0.5:
            return 'LONG'
        elif combined_score <= -0.5:
            return 'SHORT'
        else:
            return 'NO_TRADE'
            
    def _calculate_trade_parameters(
        self,
        gpt4: AIAnalysis,
        claude: AIAnalysis,
        current_price: float,
        action: str
    ) -> Dict[str, float]:
        """Calculate trade parameters"""
        # Average the AI recommendations
        target_price = (gpt4.target_price + claude.target_price) / 2
        stop_loss = (gpt4.stop_loss + claude.stop_loss) / 2
        
        # Ensure logical values
        if action == 'LONG':
            if target_price <= current_price:
                target_price = current_price * 2.0  # 2X target
            if stop_loss >= current_price:
                stop_loss = current_price * 0.95  # 5% stop loss
        else:  # SHORT
            if target_price >= current_price:
                target_price = current_price * 0.5  # 50% target for short
            if stop_loss <= current_price:
                stop_loss = current_price * 1.05  # 5% stop loss
                
        # Calculate risk/reward
        if action == 'LONG':
            risk = current_price - stop_loss
            reward = target_price - current_price
        else:
            risk = stop_loss - current_price
            reward = current_price - target_price
            
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Calculate position size based on confidence and risk
        avg_confidence = (gpt4.confidence + claude.confidence) / 2
        base_position_size = 0.1  # 10% base
        position_size = base_position_size * avg_confidence
        
        # Calculate expected return
        expected_return = (reward / current_price) * 100
        
        return {
            'target_price': target_price,
            'stop_loss': stop_loss,
            'position_size': position_size,
            'expected_return': expected_return,
            'risk_reward_ratio': risk_reward_ratio
        }
        
    def _generate_consensus_reasoning(
        self,
        gpt4: AIAnalysis,
        claude: AIAnalysis,
        technical_signals: List[TechnicalSignal],
        sentiment_data: Dict[str, SentimentData],
        agreement_score: float
    ) -> str:
        """Generate consensus reasoning"""
        reasoning_parts = []
        
        # AI agreement
        if agreement_score > 0.8:
            reasoning_parts.append("Strong agreement between AI models")
        elif agreement_score > 0.6:
            reasoning_parts.append("Moderate agreement between AI models")
        else:
            reasoning_parts.append("Limited agreement between AI models")
            
        # Technical signals
        tech_summary = self._summarize_technical_signals(technical_signals)
        reasoning_parts.append(f"Technical analysis: {tech_summary}")
        
        # Sentiment
        if 'aggregate' in sentiment_data:
            sentiment = sentiment_data['aggregate']
            if sentiment.sentiment_score > 0.3:
                reasoning_parts.append("Positive market sentiment")
            elif sentiment.sentiment_score < -0.3:
                reasoning_parts.append("Negative market sentiment")
            else:
                reasoning_parts.append("Neutral market sentiment")
                
        # Key points from AI analyses
        reasoning_parts.append(f"GPT-4: {gpt4.reasoning[:100]}...")
        reasoning_parts.append(f"Claude: {claude.reasoning[:100]}...")
        
        return " | ".join(reasoning_parts)
        
    def _identify_risk_factors(
        self,
        gpt4: AIAnalysis,
        claude: AIAnalysis,
        market_data: Dict,
        sentiment_data: Dict[str, SentimentData]
    ) -> List[str]:
        """Identify key risk factors"""
        risk_factors = []
        
        # Model disagreement
        rec_map = {
            'STRONG_BUY': 2, 'BUY': 1, 'NEUTRAL': 0, 'SELL': -1, 'STRONG_SELL': -2
        }
        if abs(rec_map.get(gpt4.recommendation, 0) - rec_map.get(claude.recommendation, 0)) > 1:
            risk_factors.append("Significant disagreement between AI models")
            
        # Low confidence
        if gpt4.confidence < 0.6 or claude.confidence < 0.6:
            risk_factors.append("Low confidence from one or more AI models")
            
        # High funding rate
        if market_data.get('funding_rate', 0) > 0.001:
            risk_factors.append("High funding rate may indicate crowded trade")
            
        # Low volume
        if market_data.get('volume_24h', 0) < 1000000:
            risk_factors.append("Low trading volume may impact liquidity")
            
        # Sentiment concerns
        if 'aggregate' in sentiment_data:
            if abs(sentiment_data['aggregate'].sentiment_score) < 0.1:
                risk_factors.append("Unclear market sentiment")
                
        return risk_factors
        
    def _summarize_technical_signals(self, signals: List[TechnicalSignal]) -> str:
        """Summarize technical signals"""
        if not signals:
            return "No technical signals available"
            
        buy_count = sum(1 for s in signals if s.signal_type == 'BUY')
        sell_count = sum(1 for s in signals if s.signal_type == 'SELL')
        
        if buy_count > sell_count:
            return f"Bullish ({buy_count} buy signals)"
        elif sell_count > buy_count:
            return f"Bearish ({sell_count} sell signals)"
        else:
            return "Mixed signals"