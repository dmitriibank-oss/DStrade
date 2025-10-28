# debug_strategy.py
import pandas as pd
import numpy as np
from config.config import Config
from src.bybit_client import BybitClient
from src.data_processor import DataProcessor
from src.logger import TradingLogger

class DebugStrategy:
    def __init__(self):
        self.client = BybitClient()
        self.data_processor = DataProcessor()
        self.logger = TradingLogger()
    
    def analyze_symbol_debug(self, symbol):
        """Детальный анализ символа с логированием всех условий"""
        self.logger.log(f"\n🔍 АНАЛИЗ {symbol}:", 'info')
        
        try:
            # Получаем данные
            df = self.client.get_klines(symbol, '15', 100)
            if df is None or len(df) < 50:
                self.logger.log(f"  ❌ Недостаточно данных: {len(df) if df else 0} строк", 'info')
                return
            
            # Расчет индикаторов
            df = self.data_processor.calculate_technical_indicators(df)
            df = self.data_processor.calculate_volatility(df)
            
            current = df.iloc[-1]
            
            # Логируем текущие значения
            self.logger.log(f"  📊 Текущая цена: {current['close']:.4f}", 'info')
            
            if 'rsi' in df.columns and not np.isnan(current['rsi']):
                self.logger.log(f"  📈 RSI: {current['rsi']:.2f} (пороги: {Config.RSI_OVERSOLD}/{Config.RSI_OVERBOUGHT})", 'info')
                
                # Проверка RSI условий
                if current['rsi'] < Config.RSI_OVERSOLD:
                    self.logger.log(f"  ✅ RSI ПЕРЕПРОДАННОСТЬ - потенциальный BUY", 'info')
                elif current['rsi'] > Config.RSI_OVERBOUGHT:
                    self.logger.log(f"  ✅ RSI ПЕРЕКУПЛЕННОСТЬ - потенциальный SELL", 'info')
                else:
                    self.logger.log(f"  ❌ RSI в нейтральной зоне", 'info')
            
            if 'ema_short' in df.columns and 'ema_long' in df.columns:
                if not np.isnan(current['ema_short']) and not np.isnan(current['ema_long']):
                    self.logger.log(f"  📊 EMA Short: {current['ema_short']:.4f}, EMA Long: {current['ema_long']:.4f}", 'info')
                    
                    # Проверка EMA кросса
                    if current['ema_short'] > current['ema_long']:
                        self.logger.log(f"  ✅ EMA BULLISH (короткая выше длинной)", 'info')
                    else:
                        self.logger.log(f"  ✅ EMA BEARISH (короткая ниже длинной)", 'info')
            
            # Проверка объема
            volume_ratio = self._calculate_volume_ratio(df)
            self.logger.log(f"  📊 Объем: {volume_ratio:.2f} от среднего (мин: {Config.MIN_VOLUME_RATIO})", 'info')
            if volume_ratio < Config.MIN_VOLUME_RATIO:
                self.logger.log(f"  ❌ СЛИШКОМ НИЗКИЙ ОБЪЕМ", 'info')
            
            # Проверка волатильности
            volatility = current['volatility'] if 'volatility' in df.columns else 0
            self.logger.log(f"  📊 Волатильность: {volatility:.4f}", 'info')
            
            # Тест стратегии
            from src.trading_strategy import TradingStrategy
            strategy = TradingStrategy()
            signal, details, strength = strategy.analyze_symbol(symbol, df)
            
            self.logger.log(f"  🎯 ИТОГОВЫЙ СИГНАЛ: {signal} (сила: {strength:.2f})", 'info')
            self.logger.log(f"  📝 Детали: {details}", 'info')
            
        except Exception as e:
            self.logger.log(f"  ❌ Ошибка анализа: {e}", 'info')
    
    def _calculate_volume_ratio(self, df):
        """Расчет отношения объема"""
        if len(df) < 20:
            return 1.0
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(20).mean()
        return current_volume / avg_volume if avg_volume > 0 else 1.0

def main():
    debug = DebugStrategy()
    
    print("=" * 50)
    print("🔍 ДИАГНОСТИКА ТОРГОВОЙ СТРАТЕГИИ")
    print("=" * 50)
    
    for symbol in Config.SYMBOLS:
        debug.analyze_symbol_debug(symbol)
    
    print("\n" + "=" * 50)
    print("📊 ТЕКУЩИЕ НАСТРОЙКИ СТРАТЕГИИ:")
    print(f"RSI пороги: {Config.RSI_OVERSOLD}/{Config.RSI_OVERBOUGHT}")
    print(f"Минимальный объем: {Config.MIN_VOLUME_RATIO}")
    print(f"Макс. позиций: {Config.MAX_POSITIONS}")
    print(f"Рик на сделку: {Config.RISK_PER_TRADE:.1%}")
    print("=" * 50)

if __name__ == "__main__":
    main()