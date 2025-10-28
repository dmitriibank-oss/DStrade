import unittest
import pandas as pd
from src.data_processor import DataProcessor
from src.trading_strategy import TradingStrategy

class TestTradingBot(unittest.TestCase):
    def setUp(self):
        self.data_processor = DataProcessor()
        self.strategy = TradingStrategy()
        
    def test_technical_indicators(self):
        # Создание тестовых данных
        data = {
            'open': [100 + i for i in range(100)],
            'high': [105 + i for i in range(100)],
            'low': [95 + i for i in range(100)],
            'close': [102 + i for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        }
        df = pd.DataFrame(data)
        
        # Проверка расчета индикаторов
        df_with_indicators = self.data_processor.calculate_technical_indicators(df)
        
        self.assertIn('rsi', df_with_indicators.columns)
        self.assertIn('ema_short', df_with_indicators.columns)
        self.assertIn('macd', df_with_indicators.columns)
        
    def test_strategy_analysis(self):
        # Создание тестовых данных с явным трендом
        data = {
            'close': [100 + i * 2 for i in range(100)]  # Восходящий тренд
        }
        df = pd.DataFrame(data)
        df = self.data_processor.calculate_technical_indicators(df)
        
        signal, details = self.strategy.analyze_symbol('TEST', df)
        
        self.assertIn(signal, ['BUY', 'SELL', 'HOLD'])

if __name__ == '__main__':
    unittest.main()