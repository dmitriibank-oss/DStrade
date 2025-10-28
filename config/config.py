import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY')
    BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET')
    
    # Валидация API ключей (только предупреждение, не ошибка)
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        print("WARNING: BYBIT_API_KEY and BYBIT_API_SECRET not set in .env file")
    
    # Trading Settings
    TESTNET = True  # Используйте True для тестовой сети
    INITIAL_BALANCE = 100  # Начальный баланс в USDT
    MAX_POSITION_SIZE = 10  # Максимальный размер позиции в USDT
    RISK_PER_TRADE = 0.02  # 2% риска на сделку
    
    # Trading Pairs (только низкоценные для тестирования)
    SYMBOLS = ['SOLUSDT', 'XRPUSDT']  # Исключили BTCUSDT и ETHUSDT из-за высокой цены
    
    # Strategy Settings
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    EMA_SHORT = 9
    EMA_LONG = 21
    
    # Risk Management
    STOP_LOSS_PCT = 0.02  # 2% стоп-лосс
    TAKE_PROFIT_PCT = 0.04  # 4% тейк-профит
    MAX_DRAWDOWN = 0.10  # 10% максимальная просадка
    
    # Telegram Notifications (опционально)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')