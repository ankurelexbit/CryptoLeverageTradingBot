import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import ta
from loguru import logger
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TechnicalSignal:
    symbol: str
    timeframe: str
    signal_type: str  # 'BUY', 'SELL', 'NEUTRAL'
    strength: float  # 0-1 scale
    indicators: Dict[str, float]
    reasoning: str
    timestamp: datetime


class TechnicalAnalyzer:
    def __init__(self):
        self.indicators_config = {
            'RSI': {'period': 14, 'oversold': 30, 'overbought': 70},
            'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
            'BB': {'period': 20, 'std': 2},
            'EMA': {'periods': [9, 21, 50, 200]},
            'ATR': {'period': 14},
            'STOCH': {'k_period': 14, 'd_period': 3, 'smooth_k': 3},
            'ADX': {'period': 14},
            'OBV': {},
            'MFI': {'period': 14}
        }
        
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> TechnicalSignal:
        """Perform comprehensive technical analysis on price data"""
        if df.empty or len(df) < 200:
            logger.warning(f"Insufficient data for {symbol} on {timeframe}")
            return TechnicalSignal(
                symbol=symbol,
                timeframe=timeframe,
                signal_type='NEUTRAL',
                strength=0.0,
                indicators={},
                reasoning="Insufficient data",
                timestamp=datetime.now()
            )
            
        # Calculate all indicators
        indicators = self._calculate_indicators(df)
        
        # Generate signals from indicators
        signals = self._generate_signals(indicators, df)
        
        # Aggregate signals
        final_signal = self._aggregate_signals(signals)
        
        # Build reasoning
        reasoning = self._build_reasoning(signals, indicators)
        
        return TechnicalSignal(
            symbol=symbol,
            timeframe=timeframe,
            signal_type=final_signal['type'],
            strength=final_signal['strength'],
            indicators=indicators,
            reasoning=reasoning,
            timestamp=datetime.now()
        )
        
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate all technical indicators"""
        indicators = {}
        
        try:
            # RSI
            rsi = ta.momentum.RSIIndicator(df['close'], window=self.indicators_config['RSI']['period'])
            indicators['rsi'] = rsi.rsi().iloc[-1]
            
            # MACD
            macd = ta.trend.MACD(
                df['close'],
                window_slow=self.indicators_config['MACD']['slow'],
                window_fast=self.indicators_config['MACD']['fast'],
                window_sign=self.indicators_config['MACD']['signal']
            )
            indicators['macd'] = macd.macd().iloc[-1]
            indicators['macd_signal'] = macd.macd_signal().iloc[-1]
            indicators['macd_diff'] = macd.macd_diff().iloc[-1]
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(
                df['close'],
                window=self.indicators_config['BB']['period'],
                window_dev=self.indicators_config['BB']['std']
            )
            indicators['bb_high'] = bb.bollinger_hband().iloc[-1]
            indicators['bb_low'] = bb.bollinger_lband().iloc[-1]
            indicators['bb_mid'] = bb.bollinger_mavg().iloc[-1]
            indicators['bb_width'] = indicators['bb_high'] - indicators['bb_low']
            indicators['bb_position'] = (df['close'].iloc[-1] - indicators['bb_low']) / indicators['bb_width']
            
            # EMAs
            for period in self.indicators_config['EMA']['periods']:
                ema = ta.trend.EMAIndicator(df['close'], window=period)
                indicators[f'ema_{period}'] = ema.ema_indicator().iloc[-1]
                
            # ATR (Average True Range)
            atr = ta.volatility.AverageTrueRange(
                df['high'], df['low'], df['close'],
                window=self.indicators_config['ATR']['period']
            )
            indicators['atr'] = atr.average_true_range().iloc[-1]
            indicators['atr_percent'] = (indicators['atr'] / df['close'].iloc[-1]) * 100
            
            # Stochastic
            stoch = ta.momentum.StochasticOscillator(
                df['high'], df['low'], df['close'],
                window=self.indicators_config['STOCH']['k_period'],
                smooth_window=self.indicators_config['STOCH']['smooth_k']
            )
            indicators['stoch_k'] = stoch.stoch().iloc[-1]
            indicators['stoch_d'] = stoch.stoch_signal().iloc[-1]
            
            # ADX (Average Directional Index)
            adx = ta.trend.ADXIndicator(
                df['high'], df['low'], df['close'],
                window=self.indicators_config['ADX']['period']
            )
            indicators['adx'] = adx.adx().iloc[-1]
            indicators['adx_pos'] = adx.adx_pos().iloc[-1]
            indicators['adx_neg'] = adx.adx_neg().iloc[-1]
            
            # OBV (On Balance Volume)
            obv = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume'])
            obv_values = obv.on_balance_volume()
            indicators['obv'] = obv_values.iloc[-1]
            indicators['obv_ema'] = ta.trend.EMAIndicator(obv_values, window=21).ema_indicator().iloc[-1]
            
            # MFI (Money Flow Index)
            mfi = ta.volume.MFIIndicator(
                df['high'], df['low'], df['close'], df['volume'],
                window=self.indicators_config['MFI']['period']
            )
            indicators['mfi'] = mfi.money_flow_index().iloc[-1]
            
            # Volume analysis
            indicators['volume_sma'] = df['volume'].rolling(window=20).mean().iloc[-1]
            indicators['volume_ratio'] = df['volume'].iloc[-1] / indicators['volume_sma']
            
            # Price action
            indicators['current_price'] = df['close'].iloc[-1]
            indicators['price_change'] = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100
            
            # Support and Resistance
            indicators['resistance'] = df['high'].rolling(window=20).max().iloc[-1]
            indicators['support'] = df['low'].rolling(window=20).min().iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            
        return indicators
        
    def _generate_signals(self, indicators: Dict[str, float], df: pd.DataFrame) -> Dict[str, Dict]:
        """Generate trading signals from indicators"""
        signals = {}
        
        # RSI Signal
        rsi_value = indicators.get('rsi', 50)
        if rsi_value < self.indicators_config['RSI']['oversold']:
            signals['rsi'] = {'signal': 'BUY', 'strength': (self.indicators_config['RSI']['oversold'] - rsi_value) / self.indicators_config['RSI']['oversold']}
        elif rsi_value > self.indicators_config['RSI']['overbought']:
            signals['rsi'] = {'signal': 'SELL', 'strength': (rsi_value - self.indicators_config['RSI']['overbought']) / (100 - self.indicators_config['RSI']['overbought'])}
        else:
            signals['rsi'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        # MACD Signal
        macd_diff = indicators.get('macd_diff', 0)
        if macd_diff > 0 and indicators.get('macd', 0) > indicators.get('macd_signal', 0):
            signals['macd'] = {'signal': 'BUY', 'strength': min(abs(macd_diff) / 0.001, 1.0)}
        elif macd_diff < 0 and indicators.get('macd', 0) < indicators.get('macd_signal', 0):
            signals['macd'] = {'signal': 'SELL', 'strength': min(abs(macd_diff) / 0.001, 1.0)}
        else:
            signals['macd'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        # Bollinger Bands Signal
        bb_position = indicators.get('bb_position', 0.5)
        if bb_position < 0.2:
            signals['bb'] = {'signal': 'BUY', 'strength': (0.2 - bb_position) / 0.2}
        elif bb_position > 0.8:
            signals['bb'] = {'signal': 'SELL', 'strength': (bb_position - 0.8) / 0.2}
        else:
            signals['bb'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        # EMA Trend Signal
        current_price = indicators.get('current_price', 0)
        ema_9 = indicators.get('ema_9', current_price)
        ema_21 = indicators.get('ema_21', current_price)
        ema_50 = indicators.get('ema_50', current_price)
        
        if current_price > ema_9 > ema_21 > ema_50:
            signals['ema_trend'] = {'signal': 'BUY', 'strength': 0.8}
        elif current_price < ema_9 < ema_21 < ema_50:
            signals['ema_trend'] = {'signal': 'SELL', 'strength': 0.8}
        else:
            signals['ema_trend'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        # Stochastic Signal
        stoch_k = indicators.get('stoch_k', 50)
        stoch_d = indicators.get('stoch_d', 50)
        if stoch_k < 20 and stoch_k > stoch_d:
            signals['stoch'] = {'signal': 'BUY', 'strength': (20 - stoch_k) / 20}
        elif stoch_k > 80 and stoch_k < stoch_d:
            signals['stoch'] = {'signal': 'SELL', 'strength': (stoch_k - 80) / 20}
        else:
            signals['stoch'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        # ADX Trend Strength
        adx = indicators.get('adx', 0)
        if adx > 25:
            if indicators.get('adx_pos', 0) > indicators.get('adx_neg', 0):
                signals['adx'] = {'signal': 'BUY', 'strength': min(adx / 50, 1.0)}
            else:
                signals['adx'] = {'signal': 'SELL', 'strength': min(adx / 50, 1.0)}
        else:
            signals['adx'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        # Volume Signal
        volume_ratio = indicators.get('volume_ratio', 1.0)
        if volume_ratio > 1.5 and indicators.get('price_change', 0) > 0:
            signals['volume'] = {'signal': 'BUY', 'strength': min((volume_ratio - 1) / 2, 1.0)}
        elif volume_ratio > 1.5 and indicators.get('price_change', 0) < 0:
            signals['volume'] = {'signal': 'SELL', 'strength': min((volume_ratio - 1) / 2, 1.0)}
        else:
            signals['volume'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        # MFI Signal
        mfi = indicators.get('mfi', 50)
        if mfi < 20:
            signals['mfi'] = {'signal': 'BUY', 'strength': (20 - mfi) / 20}
        elif mfi > 80:
            signals['mfi'] = {'signal': 'SELL', 'strength': (mfi - 80) / 20}
        else:
            signals['mfi'] = {'signal': 'NEUTRAL', 'strength': 0.0}
            
        return signals
        
    def _aggregate_signals(self, signals: Dict[str, Dict]) -> Dict[str, float]:
        """Aggregate multiple signals into a final decision"""
        buy_strength = 0
        sell_strength = 0
        neutral_count = 0
        
        weights = {
            'rsi': 0.15,
            'macd': 0.20,
            'bb': 0.10,
            'ema_trend': 0.25,
            'stoch': 0.10,
            'adx': 0.10,
            'volume': 0.05,
            'mfi': 0.05
        }
        
        for indicator, signal_data in signals.items():
            weight = weights.get(indicator, 0.1)
            
            if signal_data['signal'] == 'BUY':
                buy_strength += signal_data['strength'] * weight
            elif signal_data['signal'] == 'SELL':
                sell_strength += signal_data['strength'] * weight
            else:
                neutral_count += 1
                
        # Determine final signal
        if buy_strength > sell_strength and buy_strength > 0.3:
            return {'type': 'BUY', 'strength': min(buy_strength, 1.0)}
        elif sell_strength > buy_strength and sell_strength > 0.3:
            return {'type': 'SELL', 'strength': min(sell_strength, 1.0)}
        else:
            return {'type': 'NEUTRAL', 'strength': 0.0}
            
    def _build_reasoning(self, signals: Dict[str, Dict], indicators: Dict[str, float]) -> str:
        """Build human-readable reasoning for the signal"""
        reasoning_parts = []
        
        for indicator, signal_data in signals.items():
            if signal_data['signal'] != 'NEUTRAL':
                if indicator == 'rsi':
                    reasoning_parts.append(f"RSI at {indicators.get('rsi', 0):.2f} indicates {signal_data['signal']}")
                elif indicator == 'macd':
                    reasoning_parts.append(f"MACD crossover signals {signal_data['signal']}")
                elif indicator == 'bb':
                    reasoning_parts.append(f"Price near Bollinger Band {signal_data['signal']} zone")
                elif indicator == 'ema_trend':
                    reasoning_parts.append(f"EMA alignment shows {signal_data['signal']} trend")
                elif indicator == 'volume':
                    reasoning_parts.append(f"Volume surge confirms {signal_data['signal']} pressure")
                    
        return "; ".join(reasoning_parts) if reasoning_parts else "Mixed signals, no clear direction"