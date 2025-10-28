import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_imports():
    """Проверка всех импортов"""
    print("=== ПРОВЕРКА ИМПОРТОВ ===")
    
    try:
        from src.bybit_client import BybitClient
        print("✅ BybitClient - OK")
    except Exception as e:
        print(f"❌ BybitClient - ERROR: {e}")
    
    try:
        from src.trading_strategy import TradingStrategy
        print("✅ TradingStrategy - OK")
    except Exception as e:
        print(f"❌ TradingStrategy - ERROR: {e}")
    
    try:
        from src.risk_manager import RiskManager
        print("✅ RiskManager - OK")
    except Exception as e:
        print(f"❌ RiskManager - ERROR: {e}")
    
    try:
        from src.data_processor import DataProcessor
        print("✅ DataProcessor - OK")
    except Exception as e:
        print(f"❌ DataProcessor - ERROR: {e}")
    
    try:
        from src.position_manager import PositionManager
        print("✅ PositionManager - OK")
    except Exception as e:
        print(f"❌ PositionManager - ERROR: {e}")
    
    try:
        from src.logger import TradingLogger
        print("✅ TradingLogger - OK")
    except Exception as e:
        print(f"❌ TradingLogger - ERROR: {e}")

if __name__ == "__main__":
    load_dotenv()
    check_imports()