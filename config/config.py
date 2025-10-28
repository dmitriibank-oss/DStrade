import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

class Config:
    # API Keys
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
    BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
    
    # Валидация API ключей
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        print("WARNING: BYBIT_API_KEY and BYBIT_API_SECRET not set in .env file")
    
    # Trading Settings
    TESTNET = True
    INITIAL_BALANCE = 10000
    MAX_POSITION_SIZE = 100  # Уменьшили для снижения риска
    RISK_PER_TRADE = 0.05  # Уменьшили риск до 1%
    
    # Trading Pairs - только проверенные символы
    SYMBOLS = ['SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'DOTUSDT', 'NEARUSDT']
    
    # Dynamic Strategy Settings
    RSI_PERIOD = 14
    RSI_OVERSOLD = 32  # Ужесточили
    RSI_OVERBOUGHT = 68  # Ужесточили
    EMA_SHORT = 9
    EMA_LONG = 21
    
    # Advanced Risk Management
    STOP_LOSS_PCT = 0.02  # 1% стоп-лосс
    TAKE_PROFIT_PCT = 0.08  # 3% тейк-профит (риск 1:3)
    MAX_DRAWDOWN = 0.09  # 5% максимальная просадка
    DAILY_LOSS_LIMIT = 0.09  # 2% максимальный убыток в день
    MAX_POSITIONS = 3  # Уменьшили количество позиций
    
    # Market Filters
    MIN_VOLUME_RATIO = 0.8  # Повысили минимальный объем
    
    # Strategy Improvements
    REQUIRED_CONFIRMATIONS = 2  # Требуется подтверждение сигнала
    MIN_SIGNAL_STRENGTH = 1.5  # Минимальная сила сигнала
    
    # Order Settings
    USE_LIMIT_ORDERS = True  # Лимитные ордера для лучшего исполнения
    LIMIT_ORDER_PRICE_OFFSET = 0.002  # 0.2% отклонение
    
    # Telegram Notifications
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Performance Tracking
    SAVE_TRADES = True
    TRADE_LOG_FILE = 'trades.json'
    
    @classmethod
    def should_trade(cls, symbol, current_volatility, volume_ratio):
        """Строгие условия для торговли"""
        if current_volatility < 0.005 or current_volatility > 0.06:
            return False, "Неподходящая волатильность"
        if volume_ratio < cls.MIN_VOLUME_RATIO:
            return False, "Слишком низкий объем"
        return True, "OK"