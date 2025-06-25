from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
from loguru import logger
from src.config import settings
from src.analysis.consensus_engine import TradeRecommendation


@dataclass
class Position:
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    current_price: float
    size: float  # Position size in USDT
    stop_loss: float
    take_profit: float
    entry_time: datetime
    pnl: float
    pnl_percentage: float


@dataclass
class RiskMetrics:
    total_exposure: float
    max_drawdown: float
    current_drawdown: float
    risk_per_trade: float
    portfolio_var: float  # Value at Risk
    sharpe_ratio: float
    correlation_risk: float
    timestamp: datetime


class RiskManager:
    def __init__(self):
        self.max_position_size = settings.max_position_size
        self.risk_per_trade = settings.risk_per_trade
        self.max_concurrent_positions = settings.max_concurrent_positions
        self.max_portfolio_risk = 0.06  # 6% max portfolio risk
        self.correlation_threshold = 0.7
        self.positions: List[Position] = []
        self.historical_returns: List[float] = []
        self.account_balance = 10000  # Default in-memory balance
        
    def validate_trade(
        self,
        recommendation: TradeRecommendation,
        current_price: float,
        account_balance: float
    ) -> Tuple[bool, str, float]:
        """Validate if a trade should be taken based on risk parameters"""
        
        # Check concurrent positions limit
        if len(self.positions) >= self.max_concurrent_positions:
            return False, "Maximum concurrent positions reached", 0
            
        # Calculate position size
        position_size = self._calculate_position_size(
            recommendation, current_price, account_balance
        )
        
        # Check if position size is within limits
        if position_size > self.max_position_size:
            position_size = self.max_position_size
            
        if position_size < 10:  # Minimum position size
            return False, "Position size too small", 0
            
        # Check portfolio risk
        portfolio_risk = self._calculate_portfolio_risk(position_size, recommendation)
        if portfolio_risk > self.max_portfolio_risk:
            return False, f"Portfolio risk too high: {portfolio_risk:.2%}", 0
            
        # Check correlation with existing positions
        correlation_risk = self._check_correlation_risk(recommendation.symbol)
        if correlation_risk > self.correlation_threshold:
            return False, f"High correlation with existing positions: {correlation_risk:.2f}", 0
            
        # Validate stop loss
        if recommendation.action == 'LONG':
            risk_percentage = (current_price - recommendation.stop_loss) / current_price
        else:
            risk_percentage = (recommendation.stop_loss - current_price) / current_price
            
        if risk_percentage > 0.1:  # Max 10% stop loss
            return False, f"Stop loss too far: {risk_percentage:.2%}", 0
            
        return True, "Trade validated", position_size
        
    def _calculate_position_size(
        self,
        recommendation: TradeRecommendation,
        current_price: float,
        account_balance: float
    ) -> float:
        """Calculate appropriate position size using Kelly Criterion and risk limits"""
        
        # Basic position size from recommendation
        base_size = account_balance * recommendation.position_size_percent
        
        # Apply Kelly Criterion for optimal sizing
        win_probability = recommendation.confidence
        win_loss_ratio = recommendation.risk_reward_ratio
        
        if win_loss_ratio > 0:
            kelly_fraction = (win_probability * win_loss_ratio - (1 - win_probability)) / win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        else:
            kelly_fraction = 0
            
        kelly_size = account_balance * kelly_fraction
        
        # Use the smaller of base size and Kelly size
        position_size = min(base_size, kelly_size)
        
        # Apply risk per trade limit
        if recommendation.action == 'LONG':
            max_loss = current_price - recommendation.stop_loss
        else:
            max_loss = recommendation.stop_loss - current_price
            
        max_position_from_risk = (account_balance * self.risk_per_trade) / (max_loss / current_price)
        position_size = min(position_size, max_position_from_risk)
        
        return position_size
        
    def _calculate_portfolio_risk(self, new_position_size: float, recommendation: TradeRecommendation) -> float:
        """Calculate total portfolio risk including new position"""
        total_risk = 0
        
        # Risk from existing positions
        for position in self.positions:
            if position.side == 'LONG':
                position_risk = (position.current_price - position.stop_loss) / position.current_price
            else:
                position_risk = (position.stop_loss - position.current_price) / position.current_price
                
            total_risk += position_risk * (position.size / self._get_total_portfolio_value())
            
        # Risk from new position
        if recommendation.action == 'LONG':
            new_risk = (recommendation.entry_price - recommendation.stop_loss) / recommendation.entry_price
        else:
            new_risk = (recommendation.stop_loss - recommendation.entry_price) / recommendation.entry_price
            
        total_risk += new_risk * (new_position_size / self._get_total_portfolio_value())
        
        return total_risk
        
    def _check_correlation_risk(self, symbol: str) -> float:
        """Check correlation with existing positions"""
        if not self.positions:
            return 0
            
        # Simplified correlation check based on symbol similarity
        # In production, use actual price correlation data
        correlation_scores = []
        
        for position in self.positions:
            if position.symbol == symbol:
                correlation_scores.append(1.0)  # Same symbol = perfect correlation
            elif position.symbol[:3] == symbol[:3]:
                correlation_scores.append(0.8)  # Same base currency = high correlation
            else:
                correlation_scores.append(0.3)  # Different assets = low correlation
                
        return max(correlation_scores) if correlation_scores else 0
        
    def add_position(self, recommendation: TradeRecommendation, actual_size: float):
        """Add a new position to tracking"""
        position = Position(
            symbol=recommendation.symbol,
            side=recommendation.action,
            entry_price=recommendation.entry_price,
            current_price=recommendation.entry_price,
            size=actual_size,
            stop_loss=recommendation.stop_loss,
            take_profit=recommendation.target_price,
            entry_time=datetime.now(),
            pnl=0,
            pnl_percentage=0
        )
        self.positions.append(position)
        logger.info(f"Added position: {position}")
        
    def update_positions(self, price_updates: Dict[str, float]):
        """Update positions with current prices"""
        for position in self.positions:
            if position.symbol in price_updates:
                position.current_price = price_updates[position.symbol]
                
                # Calculate PnL
                if position.side == 'LONG':
                    position.pnl = (position.current_price - position.entry_price) * position.size / position.entry_price
                    position.pnl_percentage = (position.current_price - position.entry_price) / position.entry_price
                else:
                    position.pnl = (position.entry_price - position.current_price) * position.size / position.entry_price
                    position.pnl_percentage = (position.entry_price - position.current_price) / position.entry_price
                    
    def check_stop_loss_take_profit(self) -> List[Tuple[Position, str]]:
        """Check if any positions hit stop loss or take profit"""
        positions_to_close = []
        
        for position in self.positions:
            if position.side == 'LONG':
                if position.current_price <= position.stop_loss:
                    positions_to_close.append((position, 'STOP_LOSS'))
                elif position.current_price >= position.take_profit:
                    positions_to_close.append((position, 'TAKE_PROFIT'))
            else:  # SHORT
                if position.current_price >= position.stop_loss:
                    positions_to_close.append((position, 'STOP_LOSS'))
                elif position.current_price <= position.take_profit:
                    positions_to_close.append((position, 'TAKE_PROFIT'))
                    
        return positions_to_close
        
    def apply_trailing_stop(self):
        """Apply trailing stop to profitable positions"""
        for position in self.positions:
            if position.pnl_percentage > 0.05:  # 5% profit threshold
                if position.side == 'LONG':
                    new_stop = position.current_price * (1 - settings.trailing_stop_percentage)
                    if new_stop > position.stop_loss:
                        position.stop_loss = new_stop
                        logger.info(f"Updated trailing stop for {position.symbol} to {new_stop}")
                else:  # SHORT
                    new_stop = position.current_price * (1 + settings.trailing_stop_percentage)
                    if new_stop < position.stop_loss:
                        position.stop_loss = new_stop
                        logger.info(f"Updated trailing stop for {position.symbol} to {new_stop}")
                        
    def close_position(self, position: Position):
        """Close a position and record the return"""
        self.positions.remove(position)
        self.historical_returns.append(position.pnl_percentage)
        logger.info(f"Closed position: {position.symbol} with {position.pnl_percentage:.2%} return")
        
    def get_risk_metrics(self) -> RiskMetrics:
        """Calculate current risk metrics"""
        total_exposure = sum(p.size for p in self.positions)
        
        # Calculate drawdown
        if self.historical_returns:
            cumulative_returns = np.cumprod(1 + np.array(self.historical_returns))
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
            current_drawdown = drawdown[-1] if len(drawdown) > 0 else 0
        else:
            max_drawdown = 0
            current_drawdown = 0
            
        # Calculate VaR (95% confidence)
        if len(self.historical_returns) > 20:
            var_95 = np.percentile(self.historical_returns, 5)
        else:
            var_95 = -self.risk_per_trade
            
        # Calculate Sharpe Ratio
        if len(self.historical_returns) > 1:
            returns_array = np.array(self.historical_returns)
            sharpe_ratio = np.mean(returns_array) / (np.std(returns_array) + 1e-6) * np.sqrt(252)
        else:
            sharpe_ratio = 0
            
        # Correlation risk
        correlation_risk = self._calculate_portfolio_correlation()
        
        return RiskMetrics(
            total_exposure=total_exposure,
            max_drawdown=max_drawdown,
            current_drawdown=current_drawdown,
            risk_per_trade=self.risk_per_trade,
            portfolio_var=var_95,
            sharpe_ratio=sharpe_ratio,
            correlation_risk=correlation_risk,
            timestamp=datetime.now()
        )
        
    def _get_total_portfolio_value(self) -> float:
        """Get total portfolio value including positions"""
        # This should be connected to actual account balance
        # For now, return a default value
        return 10000
        
    def _calculate_portfolio_correlation(self) -> float:
        """Calculate average correlation in portfolio"""
        if len(self.positions) < 2:
            return 0
            
        # Simplified calculation
        same_base_pairs = defaultdict(int)
        for position in self.positions:
            base = position.symbol[:3]
            same_base_pairs[base] += 1
            
        max_concentration = max(same_base_pairs.values()) if same_base_pairs else 1
        correlation_risk = (max_concentration - 1) / len(self.positions)
        
        return correlation_risk