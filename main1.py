import os
import sys
import signal
import atexit
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from server.api.bybit import BybitAPI
from strategies.trading_strategy import TradingStrategy
from simple_trading_engine import SimpleTradingEngine  # Используем упрощенную версию
from config import Config

def cleanup():
    print("\nPerforming cleanup...")

def signal_handler(sig, frame):
    print('\nShutting down gracefully...')
    cleanup()
    sys.exit(0)

def main():
    load_dotenv()
    
    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup)
    
    required_vars = ['BYBIT_API_KEY', 'BYBIT_API_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    try:
        config = Config()
        api = BybitAPI()
        strategy = TradingStrategy(config)
        engine = SimpleTradingEngine(api, strategy, config)  # Упрощенный движок
        
        print("🚀 DStrade Simple Bot Starting...")
        print("==================================================")
        print(f"📊 Trading Pairs: {', '.join(config.TRADING_PAIRS)}")
        print(f"💰 Fixed Position Sizes")
        print(f"🎯 Max Concurrent Trades: {config.MAX_CONCURRENT_TRADES}")
        print("==================================================")
        print("Press Ctrl+C to stop")
        print("==================================================")
        
        engine.run()
        
    except Exception as e:
        print(f"❌ Failed to start trading bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()