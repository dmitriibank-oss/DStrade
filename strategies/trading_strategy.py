import pandas as pd
import numpy as np
from typing import Dict, Optional
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    from .technical_indicators import TechnicalIndicators

class TradingStrategy:
    def __init__(self, config):
        self.config = config
        self.indicators = TechnicalIndicators() if not TALIB_AVAILABLE else None
        self.previous_signal = 'HOLD'
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Расчет технических индикаторов"""
        # RSI
        if self.config.ENABLE_RSI:
            if TALIB_AVAILABLE:
                df['rsi'] = talib.RSI(df['close'], timeperiod=self.config.RSI_PERIOD)
            else:
                df['rsi'] = self.indicators.rsi(df['close'], period=self.config.RSI_PERIOD)
        
        # MACD
        if self.config.ENABLE_MACD:
            if TALIB_AVAILABLE:
                macd, macd_signal, macd_hist = talib.MACD(
                    df['close'], 
                    fastperiod=self.config.MACD_FAST,
                    slowperiod=self.config.MACD_SLOW, 
                    signalperiod=self.config.MACD_SIGNAL
                )
            else:
                macd, macd_signal, macd_hist = self.indicators.macd(
                    df['close'], 
                    fast=self.config.MACD_FAST,
                    slow=self.config.MACD_SLOW, 
                    signal=self.config.MACD_SIGNAL
                )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist
        
        # EMA
        if self.config.ENABLE_EMA:
            if TALIB_AVAILABLE:
                df['ema_20'] = talib.EMA(df['close'], timeperiod=20)
                df['ema_50'] = talib.EMA(df['close'], timeperiod=50)
                df['ema_100'] = talib.EMA(df['close'], timeperiod=100)
            else:
                df['ema_20'] = self.indicators.ema(df['close'], period=20)
                df['ema_50'] = self.indicators.ema(df['close'], period=50)
                df['ema_100'] = self.indicators.ema(df['close'], period=100)
        
        # Дополнительные индикаторы
        df['price_change'] = df['close'].pct_change()
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        return df

    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """Генерация торговых сигналов - более агрессивная версия для тестирования"""
        if len(df) < 100:
            return {'signal': 'HOLD', 'reason': 'Insufficient data'}
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Проверка на NaN значения
        required_indicators = ['rsi', 'macd', 'macd_signal', 'ema_20', 'ema_50']
        if any(pd.isna(latest[key]) for key in required_indicators):
            return {'signal': 'HOLD', 'reason': 'Indicators not ready'}
        
        # Более агрессивные настройки для тестирования
        rsi_signal = self._get_aggressive_rsi_signal(latest)
        macd_signal = self._get_aggressive_macd_signal(latest, prev)
        trend_signal = self._get_trend_signal(latest, prev)
        volume_signal = self._get_volume_signal(latest, df)
        
        # Система весов для сигналов
        signals_weight = {
            'RSI': rsi_signal,
            'MACD': macd_signal, 
            'TREND': trend_signal,
            'VOLUME': volume_signal
        }
        
        # Подсчет баллов (более агрессивный порог)
        buy_points = 0
        sell_points = 0
        
        for indicator, signal in signals_weight.items():
            if signal == 'BUY':
                buy_points += 1
            elif signal == 'SELL':
                sell_points += 1
        
        # Генерация финального сигнала (более низкий порог)
        if buy_points >= 2:  # Было 3
            final_signal = 'BUY'
            reason = f"Aggressive buy ({buy_points}/4 indicators)"
        elif sell_points >= 2:  # Было 3
            final_signal = 'SELL'
            reason = f"Aggressive sell ({sell_points}/4 indicators)"
        else:
            final_signal = 'HOLD'
            reason = f"Mixed signals (Buy: {buy_points}, Sell: {sell_points})"
        
        return {
            'signal': final_signal,
            'reason': reason,
            'details': signals_weight
        }

    def _get_aggressive_rsi_signal(self, data) -> str:
        """Более агрессивные RSI сигналы"""
        rsi = data['rsi']
        
        if rsi < 40:  # Было 35
            return 'BUY'
        elif rsi > 60:  # Было 65
            return 'SELL'
        else:
            return 'HOLD'

    def _get_aggressive_macd_signal(self, current, previous) -> str:
        """Более агрессивные MACD сигналы"""
        # MACD выше нуля - покупаем, ниже - продаем
        if current['macd'] > 0:
            return 'BUY'
        elif current['macd'] < 0:
            return 'SELL'
        else:
            return 'HOLD'

    def _get_rsi_signal(self, data) -> str:
        """RSI-based signals с зонами перекупленности/перепроданности"""
        rsi = data['rsi']
        
        if rsi < 25:  # Сильная перепроданность
            return 'BUY'
        elif rsi > 75:  # Сильная перекупленность
            return 'SELL'
        elif rsi < 35:  # Перепроданность
            return 'BUY'
        elif rsi > 65:  # Перекупленность
            return 'SELL'
        else:
            return 'HOLD'

    def _get_macd_signal(self, current, previous) -> str:
        """MACD-based signals с гистограммой"""
        if (previous['macd'] < previous['macd_signal'] and 
            current['macd'] > current['macd_signal']):
            return 'BUY'
        elif (previous['macd'] > previous['macd_signal'] and 
              current['macd'] < current['macd_signal']):
            return 'SELL'
        elif current['macd_hist'] > 0 and current['macd'] > 0:
            return 'BUY'
        elif current['macd_hist'] < 0 and current['macd'] < 0:
            return 'SELL'
        else:
            return 'HOLD'

    def _get_trend_signal(self, current, previous) -> str:
        """Trend-based signals с несколькими EMA"""
        # Краткосрочный тренд
        short_trend = 'BUY' if current['ema_20'] > current['ema_50'] else 'SELL'
        
        # Долгосрочный тренд (если доступен)
        if 'ema_100' in current and not pd.isna(current['ema_100']):
            long_trend = 'BUY' if current['ema_50'] > current['ema_100'] else 'SELL'
            if short_trend == long_trend:
                return short_trend
        
        return short_trend

    def _get_volume_signal(self, current, df) -> str:
        """Volume-based signals"""
        if 'volume_sma' not in current or pd.isna(current['volume_sma']):
            return 'HOLD'
            
        # Объем выше среднего может подтверждать тренд
        if current['volume'] > current['volume_sma'] * 1.2:
            # Анализируем направление цены
            price_change = current['price_change'] if 'price_change' in current else 0
            if price_change > 0:
                return 'BUY'
            elif price_change < 0:
                return 'SELL'
                
        return 'HOLD'