import pandas as pd
import numpy as np
from typing import Dict, List
import logging

class PairAnalyzer:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Расчет волатильности пары"""
        returns = df['close'].pct_change().dropna()
        volatility = returns.rolling(window=period).std().iloc[-1]
        return volatility * 100  # В процентах
        
    def calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Расчет силы тренда"""
        if len(df) < 50:
            return 0
            
        # Используем ADX для силы тренда (упрощенная версия)
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Расчет +DM и -DM
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        # Упрощенный расчет силы тренда
        price_change = close.pct_change().abs()
        trend_strength = price_change.rolling(window=14).mean().iloc[-1] * 100
        
        return trend_strength
        
    def analyze_pair_suitability(self, df: pd.DataFrame, pair: str) -> Dict:
        """Анализ пригодности пары для торговли"""
        if len(df) < 50:
            return {'suitable': False, 'reason': 'Insufficient data'}
            
        volatility = self.calculate_volatility(df)
        trend_strength = self.calculate_trend_strength(df)
        
        # Критерии пригодности
        suitable_volatility = 0.5 <= volatility <= 10.0  # Примерный диапазон
        has_trend = trend_strength > 0.1
        
        analysis = {
            'pair': pair,
            'volatility': volatility,
            'trend_strength': trend_strength,
            'suitable': suitable_volatility and has_trend,
            'reasons': []
        }
        
        if not suitable_volatility:
            analysis['reasons'].append(f"Volatility {volatility:.2f}% outside optimal range")
        if not has_trend:
            analysis['reasons'].append("No clear trend detected")
            
        return analysis
        
    def recommend_position_size(self, pair: str, volatility: float, account_balance: float) -> float:
        """Рекомендация размера позиции на основе волатильности"""
        base_settings = self.config.get_pair_settings(pair)
        base_amount = base_settings['trade_amount']
        
        # Корректировка на волатильность (меньшая позиция для более волатильных пар)
        volatility_factor = max(0.5, min(2.0, 2.0 / (volatility + 0.1)))
        adjusted_amount = base_amount * volatility_factor
        
        return adjusted_amount