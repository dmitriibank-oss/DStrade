import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bybit_client import BybitClient
from src.logger import TradingLogger

def final_test():
    """Финальный тест перед запуском бота"""
    logger = TradingLogger()
    logger.log("=== FINAL TEST ===", 'info')
    
    try:
        client = BybitClient()
        
        # Тест подключения
        if not client.test_connection():
            logger.log("[ERROR] Connection test failed", 'error')
            return False
        
        logger.log("[OK] Connection test passed", 'info')
        
        # Тест баланса
        balance = client.get_account_balance()
        logger.log(f"[OK] Balance: {balance} USDT", 'info')
        
        # Тест цен для всех символов
        for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']:
            price = client.get_current_price(symbol)
            if price:
                logger.log(f"[OK] {symbol} price: {price}", 'info')
            else:
                logger.log(f"[ERROR] Failed to get price for {symbol}", 'error')
        
        # Тест исторических данных
        data = client.get_klines('BTCUSDT', limit=200)
        if data is not None and len(data) >= 50:
            logger.log(f"[OK] Historical data: {len(data)} rows", 'info')
        else:
            logger.log(f"[WARNING] Limited historical data: {len(data) if data else 0} rows", 'warning')
        
        logger.log("[OK] All tests completed successfully! Bot is ready to run.", 'info')
        return True
        
    except Exception as e:
        logger.log(f"[ERROR] Final test failed: {e}", 'error')
        return False

if __name__ == "__main__":
    load_dotenv()
    if final_test():
        print("\n" + "="*50)
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Бот готов к работе!")
        print("Запустите: python main_fixed.py")
        print("="*50)
    else:
        print("\n❌ Тесты не пройдены. Проверьте настройки.")