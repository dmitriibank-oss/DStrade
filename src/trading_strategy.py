import pandas as pd
import numpy as np
from config.config import Config
from src.data_processor import DataProcessor
from src.logger import TradingLogger

class TradingStrategy:
    def __init__(self):
        self.data_processor = DataProcessor()
        self.logger = TradingLogger()
        self.min_volatility = 0.002  # Минимальная волатильность 0.2%
        self.max_volatility = 0.05   # Максимальная волатильность 5%
        self.consecutive_signals_required = 2  # Требуется 2 последовательных сигнала
    
    def analyze_symbol(self, symbol, df):
        """Улучшенный анализ с фильтрами"""
        try:
            if df is None or len(df) < 100:  # Увеличили минимальное количество данных
                return 'HOLD', ["Недостаточно данных"]
            
            # Расчет всех индикаторов
            df = self.data_processor.calculate_technical_indicators(df)
            df = self.data_processor.detect_support_resistance(df)
            df = self.data_processor.calculate_volatility(df)
            df = self.data_processor.add_price_features(df)
            
            # Фильтр волатильности
            current_volatility = df['volatility'].iloc[-1] if 'volatility' in df.columns else 0
            if current_volatility < self.min_volatility:
                return 'HOLD', ["Слишком низкая волатильность"]
            if current_volatility > self.max_volatility:
                return 'HOLD', ["Слишком высокая волатильность"]
            
            # Фильтр объема
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].tail(20).mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            if volume_ratio < 0.8:
                return 'HOLD', ["Низкий объем"]
            
            # Генерация сигналов
            signals = self._generate_trading_signals(df)
            
            return self._evaluate_signals(signals)
            
        except Exception as e:
            self.logger.log(f"Error analyzing {symbol}: {e}", 'error')
            return 'HOLD', ["Ошибка анализа"]
    
    def _generate_trading_signals(self, df):
        """Генерация торговых сигналов с весами"""
        signals = []
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # RSI с весами
        rsi_weight = 1.5
        if not np.isnan(current['rsi']):
            if current['rsi'] < 30 and prev['rsi'] >= 30:
                signals.append(('RSI_OVERSOLD_BUY', rsi_weight))
            elif current['rsi'] > 70 and prev['rsi'] <= 70:
                signals.append(('RSI_OVERBOUGHT_SELL', rsi_weight))
        
        # EMA с весами
        ema_weight = 1.2
        if not np.isnan(current['ema_short']) and not np.isnan(current['ema_long']):
            if (current['ema_short'] > current['ema_long'] and 
                prev['ema_short'] <= prev['ema_long']):
                signals.append(('EMA_GOLDEN_CROSS', ema_weight))
            elif (current['ema_short'] < current['ema_long'] and 
                  prev['ema_short'] >= prev['ema_long']):
                signals.append(('EMA_DEATH_CROSS', ema_weight))
        
        # MACD с весами
        macd_weight = 1.3
        if not np.isnan(current['macd']) and not np.isnan(current['macd_signal']):
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal']):
                signals.append(('MACD_BUY', macd_weight))
            elif (current['macd'] < current['macd_signal'] and 
                  prev['macd'] >= prev['macd_signal']):
                signals.append(('MACD_SELL', macd_weight))
        
        # Bollinger Bands
        bb_weight = 1.1
        if not np.isnan(current['bb_lower']) and not np.isnan(current['bb_upper']):
            if current['close'] < current['bb_lower']:
                signals.append(('BB_OVERSOLD', bb_weight))
            elif current['close'] > current['bb_upper']:
                signals.append(('BB_OVERBOUGHT', bb_weight))
        
        # Тренд (дополнительный фильтр)
        trend_weight = 1.1
        if not np.isnan(current['ema_long']):
            if current['close'] > current['ema_long']:
                signals.append(('UPTREND', trend_weight))
            else:
                signals.append(('DOWNTREND', trend_weight))
        
        # Support/Resistance
        sr_weight = 1.0
        if not np.isnan(current['support']) and not np.isnan(current['resistance']):
            support_distance = (current['close'] - current['support']) / current['close']
            resistance_distance = (current['resistance'] - current['close']) / current['close']
            
            if support_distance < 0.01:  # 1% от поддержки
                signals.append(('NEAR_SUPPORT', sr_weight))
            if resistance_distance < 0.01:  # 1% от сопротивления
                signals.append(('NEAR_RESISTANCE', sr_weight))
        
        return signals
    
    def _evaluate_signals(self, signals):
        """Оценка сигналов с весами"""
        if not signals:
            return 'HOLD', []
        
        buy_score = 0
        sell_score = 0
        signal_details = []
        
        for signal, weight in signals:
            signal_details.append(signal)
            
            if 'BUY' in signal or 'GOLDEN' in signal or 'UPTREND' in signal or 'OVERSOLD' in signal or 'NEAR_SUPPORT' in signal:
                buy_score += weight
            elif 'SELL' in signal or 'DEATH' in signal or 'DOWNTREND' in signal or 'OVERBOUGHT' in signal or 'NEAR_RESISTANCE' in signal:
                sell_score += weight
        
        # Порог для входа в сделку
        threshold = 2.5
        
        if buy_score - sell_score > threshold:
            return 'BUY', signal_details
        elif sell_score - buy_score > threshold:
            return 'SELL', signal_details
        else:
            return 'HOLD', signal_details

    def calculate_position_size(self, balance, current_price, stop_loss_price):
        """Расчет размера позиции на основе управления рисками"""
        risk_amount = balance * Config.RISK_PER_TRADE
        price_diff = abs(current_price - stop_loss_price)
        
        if price_diff == 0:
            return 0
            
        position_size = risk_amount / price_diff
        max_size = Config.MAX_POSITION_SIZE / current_price
        
        return min(position_size, max_size)