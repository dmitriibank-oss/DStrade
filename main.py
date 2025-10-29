import os
import sys
import signal
import atexit
from dotenv import load_dotenv

# Добавление путей для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from enhanced_monitor import enhanced_monitor
except ImportError as e:
    print(f"Note: Enhanced monitor not available: {e}")
    enhanced_monitor = None

from server.api.bybit import BybitAPI
from strategies.trading_strategy import TradingStrategy
from core.trading_engine import TradingEngine
from config import Config

def cleanup():
    """Функция очистки при завершении"""
    print("\nPerforming cleanup...")
    if enhanced_monitor:
        try:
            enhanced_monitor.save_history()
            report = enhanced_monitor.generate_detailed_report()
            print("\n=== FINAL TRADING REPORT ===")
            print(f"Total cycles: {report['summary']['total_cycles']}")
            print(f"Trading pairs: {report['summary']['unique_pairs']}")
            if 'signals_analysis' in report and 'total_signals' in report['signals_analysis']:
                print(f"Signal distribution: {report['signals_analysis']['total_signals']}")
        except Exception as e:
            print(f"Error during cleanup: {e}")

def signal_handler(sig, frame):
    print('\nShutting down gracefully...')
    cleanup()
    sys.exit(0)

def main():
    """Основная функция запуска торгового бота"""
    # Загрузка переменных окружения
    load_dotenv()
    
    # Регистрация обработчиков завершения
    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup)
    
    # Проверка обязательных переменных
    required_vars = ['BYBIT_API_KEY', 'BYBIT_API_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return
    
    # Инициализация компонентов
    try:
        config = Config()
        api = BybitAPI()
        strategy = TradingStrategy(config)
        engine = TradingEngine(api, strategy, config)
        
        print("🚀 DStrade Multi-Pair Bot Starting...")
        print("="*50)
        print(f"📊 Trading Pairs: {', '.join(config.TRADING_PAIRS)}")
        print(f"💰 Base Trade Amount: {config.BASE_TRADE_AMOUNT} USDT")
        print(f"🎯 Max Concurrent Trades: {config.MAX_CONCURRENT_TRADES}")
        print(f"⚙️  Risk Management: Enabled")
        print(f"📈 Portfolio Diversification: {'Enabled' if config.ENABLE_PORTFOLIO_DIVERSIFICATION else 'Disabled'}")
        print("="*50)
        print("Press Ctrl+C to stop")
        print("="*50)
        
        # Запуск торгового движка
        engine.run()
        
    except Exception as e:
        print(f"❌ Failed to start trading bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()