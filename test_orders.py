import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bybit_client import BybitClient
from src.logger import TradingLogger

def test_order_placement():
    """Тестирование размещения ордеров"""
    logger = TradingLogger()
    logger.log("=== ТЕСТИРОВАНИЕ РАЗМЕЩЕНИЯ ОРДЕРОВ ===", 'info')
    
    try:
        client = BybitClient()
        
        # Тест подключения
        if not client.test_connection():
            logger.log("Не удалось подключиться к API", 'error')
            return False
        
        # Тестируем ордера на разных символах
        test_symbols = [
            ('SOLUSDT', 156.85, 0.1),   # SOLUSDT с размером 0.1
            ('XRPUSDT', 4.2159, 10.0),  # XRPUSDT с размером 10.0
        ]
        
        for symbol, test_price, test_size in test_symbols:
            logger.log(f"Тестирование ордера для {symbol}...", 'info')
            
            # Тест BUY ордера
            logger.log(f"Пробуем BUY ордер для {symbol}", 'info')
            order = client.place_order(symbol, "BUY", test_size)
            
            if order:
                logger.log(f"✅ BUY ордер для {symbol} УСПЕШЕН!", 'info')
            else:
                logger.log(f"❌ BUY ордер для {symbol} НЕ УДАЛСЯ", 'error')
            
            # Небольшая пауза
            import time
            time.sleep(2)
            
            # Тест SELL ордера
            logger.log(f"Пробуем SELL ордер для {symbol}", 'info')
            order = client.place_order(symbol, "SELL", test_size)
            
            if order:
                logger.log(f"✅ SELL ордер для {symbol} УСПЕШЕН!", 'info')
            else:
                logger.log(f"❌ SELL ордер для {symbol} НЕ УДАЛСЯ", 'error')
            
            # Пауза между символами
            time.sleep(2)
        
        logger.log("=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===", 'info')
        return True
        
    except Exception as e:
        logger.log(f"Ошибка тестирования ордеров: {e}", 'error')
        return False

if __name__ == "__main__":
    load_dotenv()
    if test_order_placement():
        print("\n✅ Тестирование ордеров завершено успешно!")
    else:
        print("\n❌ Тестирование ордеров выявило проблемы!")