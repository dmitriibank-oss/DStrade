import os
import sys
from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bybit_client import BybitClient
from src.logger import TradingLogger

def diagnostic_test():
    """Диагностический тест подключения к testnet"""
    logger = TradingLogger()
    logger.log("=== STARTING DIAGNOSTIC TEST ===", 'info')
    
    try:
        # 1. Создаем клиент
        logger.log("Step 1: Creating Bybit client...", 'info')
        client = BybitClient()
        
        # 2. Тестируем базовое подключение
        logger.log("Step 2: Testing API connection...", 'info')
        connection_ok = client.test_connection()
        
        if not connection_ok:
            logger.log("✗ Basic API connection failed", 'error')
            return False
        
        logger.log("✓ Basic API connection successful", 'info')
        
        # 3. Тестируем получение баланса
        logger.log("Step 3: Testing balance retrieval...", 'info')
        balance = client.get_account_balance()
        logger.log(f"Balance result: {balance}", 'info')
        
        # 4. Тестируем получение цен
        logger.log("Step 4: Testing price data...", 'info')
        symbols = ['BTCUSDT', 'ETHUSDT']
        for symbol in symbols:
            price = client.get_current_price(symbol)
            if price:
                logger.log(f"✓ {symbol} price: {price}", 'info')
            else:
                logger.log(f"✗ Failed to get price for {symbol}", 'error')
        
        # 5. Тестируем исторические данные
        logger.log("Step 5: Testing historical data...", 'info')
        data = client.get_klines('BTCUSDT', limit=5)
        if data is not None:
            logger.log(f"✓ Historical data: {len(data)} rows", 'info')
            logger.log(f"Sample data:\n{data[['timestamp', 'close']].head()}", 'info')
        else:
            logger.log("✗ Failed to get historical data", 'error')
        
        logger.log("=== DIAGNOSTIC TEST COMPLETED ===", 'info')
        return True
        
    except Exception as e:
        logger.log(f"✗ Diagnostic test failed: {e}", 'error')
        return False

if __name__ == "__main__":
    load_dotenv()
    success = diagnostic_test()
    if success:
        print("\n🎉 All tests passed! You can now run the main bot.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")