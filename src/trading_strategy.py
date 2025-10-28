import pandas as pd
import numpy as np
from config.config import Config
from src.data_processor import DataProcessor
from src.logger import TradingLogger

class TradingStrategy:
    def __init__(self):
        self.data_processor = DataProcessor()
        self.logger = TradingLogger()
        self.signal_history = {}
    
    def analyze_symbol(self, symbol, df):
        """Консервативный анализ с множеством фильтров"""
        try:
            if df is None or len(df) < 100:
                return 'HOLD', ["Недостаточно данных"], 0
            
            # Расчет индикаторов
            df = self.data_processor.calculate_technical_indicators(df)
            df = self.data_processor.calculate_volatility(df)
            
            # Фильтр объема
            volume_ratio = self._calculate_volume_ratio(df)
            current_volatility = df['volatility'].iloc[-1] if 'volatility' in df.columns else 0.02
            
            # Проверка условий торговли
            can_trade, reason = Config.should_trade(symbol, current_volatility, volume_ratio)
            if not can_trade:
                return 'HOLD', [reason], 0
            
            # Получаем сигналы
            signals = self._get_conservative_signals(df)
            signal_strength = self._calculate_signal_strength(signals)
            
            # Требуем сильный сигнал
            if signal_strength >= Config.MIN_SIGNAL_STRENGTH:
                if signals['buy'] > signals['sell']:
                    return 'BUY', signals['details'], signal_strength
                else:
                    return 'SELL', signals['details'], signal_strength
            else:
                return 'HOLD', ["Слабый сигнал"], signal_strength
            
        except Exception as e:
            self.logger.log(f"Error analyzing {symbol}: {e}", 'error')
            return 'HOLD', ["Ошибка анализа"], 0
    
    def _get_conservative_signals(self, df):
        """Консервативные сигналы с подтверждением"""
        current = df.iloc[-1]
        prev_1 = df.iloc[-2]
        prev_2 = df.iloc[-3]
        
        signals = {'buy': 0, 'sell': 0, 'details': []}
        
        # RSI с подтверждением
        if not np.isnan(current['rsi']):
            if (current['rsi'] < Config.RSI_OVERSOLD and 
                prev_1['rsi'] < Config.RSI_OVERSOLD):
                signals['buy'] += 2.0
                signals['details'].append('RSI_OVERSOLD_CONFIRMED')
            elif (current['rsi'] > Config.RSI_OVERBOUGHT and 
                  prev_1['rsi'] > Config.RSI_OVERBOUGHT):
                signals['sell'] += 2.0
                signals['details'].append('RSI_OVERBOUGHT_CONFIRMED')
        
        # EMA кросс с подтверждением
        if not np.isnan(current['ema_short']) and not np.isnan(current['ema_long']):
            if (current['ema_short'] > current['ema_long'] and 
                prev_1['ema_short'] > prev_1['ema_long'] and
                prev_2['ema_short'] <= prev_2['ema_long']):
                signals['buy'] += 1.5
                signals['details'].append('EMA_GOLDEN_CROSS_CONFIRMED')
            elif (current['ema_short'] < current['ema_long'] and 
                  prev_1['ema_short'] < prev_1['ema_long'] and
                  prev_2['ema_short'] >= prev_2['ema_long']):
                signals['sell'] += 1.5
                signals['details'].append('EMA_DEATH_CROSS_CONFIRMED')
        
        # Тренд фильтр
        if current['close'] > current['ema_long']:
            signals['buy'] += 0.5
        else:
            signals['sell'] += 0.5
        
        # Поддержка/сопротивление
        support_resistance_signal = self._check_support_resistance(df)
        if support_resistance_signal == 'BUY':
            signals['buy'] += 1.0
            signals['details'].append('NEAR_SUPPORT')
        elif support_resistance_signal == 'SELL':
            signals['sell'] += 1.0
            signals['details'].append('NEAR_RESISTANCE')
        
        return signals
    
    def _check_support_resistance(self, df):
        """Проверка уровней поддержки и сопротивления"""
        if len(df) < 20:
            return 'HOLD'
        
        current_price = df['close'].iloc[-1]
        resistance = df['high'].tail(20).max()
        support = df['low'].tail(20).min()
        
        resistance_distance = (resistance - current_price) / current_price
        support_distance = (current_price - support) / current_price
        
        if support_distance < 0.01:  # 1% от поддержки
            return 'BUY'
        elif resistance_distance < 0.01:  # 1% от сопротивления
            return 'SELL'
        
        return 'HOLD'
    
    def _calculate_signal_strength(self, signals):
        """Расчет силы сигнала"""
        return abs(signals['buy'] - signals['sell'])
    
    def _calculate_volume_ratio(self, df):
        """Расчет отношения объема"""
        if len(df) < 20:
            return 1.0
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(20).mean()
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    def calculate_position_size(self, balance, current_price, stop_loss_price, signal_strength):
        """Консервативный расчет размера позиции"""
        # Базовый риск
        risk_amount = balance * Config.RISK_PER_TRADE
        
        # Корректировка на силу сигнала (максимум +50%)
        strength_multiplier = min(1.5, 1.0 + (signal_strength - Config.MIN_SIGNAL_STRENGTH) * 0.1)
        risk_amount *= strength_multiplier
        
        # Расчет размера позиции
        price_diff = abs(current_price - stop_loss_price)
        if price_diff == 0:
            return 0
            
        position_size = risk_amount / price_diff
        max_size = Config.MAX_POSITION_SIZE / current_price
        
        return min(position_size, max_size)