import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
    BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
    BYBIT_TESTNET = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'
    
    # Trading Configuration - Multiple Pairs
    TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'BTCUSDT,ETHUSDT,ADAUSDT,SOLUSDT').split(',')
    BASE_TRADE_AMOUNT = float(os.getenv('BASE_TRADE_AMOUNT', '100'))  # Базовая сумма в USDT
    LEVERAGE = int(os.getenv('LEVERAGE', '10'))
    
    # Обновите PAIR_SETTINGS в config.py
    PAIR_SETTINGS = {
        # Основные пары (примерно 100 USDT на сделку)
        'BTCUSDT': {'trade_amount': 0.002, 'leverage': 10},     # ~80-100 USDT
        'ETHUSDT': {'trade_amount': 0.05, 'leverage': 15},      # ~100-150 USDT  
        'ADAUSDT': {'trade_amount': 1000, 'leverage': 20},      # ~100-120 USDT
        'SOLUSDT': {'trade_amount': 5, 'leverage': 15},         # ~100-150 USDT
        'XRPUSDT': {'trade_amount': 500, 'leverage': 20},       # ~100-120 USDT
        
        # Дополнительные пары
        'DOTUSDT': {'trade_amount': 25, 'leverage': 15},        # ~100-125 USDT
        'LINKUSDT': {'trade_amount': 10, 'leverage': 15},       # ~100-120 USDT
        'LTCUSDT': {'trade_amount': 1, 'leverage': 15},         # ~80-100 USDT
        'AVAXUSDT': {'trade_amount': 5, 'leverage': 15},        # ~100-150 USDT
        'MATICUSDT': {'trade_amount': 150, 'leverage': 20},     # ~100-120 USDT
    }
    
    # API v5 Configuration
    ACCOUNT_TYPE = "UNIFIED"
    CATEGORY = "linear"  # linear, inverse, spot
    
    # Strategy Configuration
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Risk Management
    STOP_LOSS_PERCENT = 2.0
    TAKE_PROFIT_PERCENT = 4.0
    MAX_POSITION_SIZE = 0.1  # 10% от баланса на одну пару
    MAX_CONCURRENT_TRADES = 3  # Максимальное количество одновременных сделок
    
    # Technical Analysis
    ENABLE_RSI = True
    ENABLE_MACD = True
    ENABLE_EMA = True
    
    # Portfolio Management
    ENABLE_PORTFOLIO_DIVERSIFICATION = True
    CORRELATION_THRESHOLD = 0.7  # Максимальная корреляция между активами
    
    # Logging
    LOG_LEVEL = 'INFO'
    
    def get_pair_settings(self, pair):
        """Получение настроек для конкретной пары"""
        if pair in self.PAIR_SETTINGS:
            return self.PAIR_SETTINGS[pair]
        else:
            # Значения по умолчанию для новых пар
            return {'trade_amount': self.BASE_TRADE_AMOUNT, 'leverage': self.LEVERAGE}