import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.symbol_info import SymbolInfo
from src.bybit_client import BybitClient
from src.logger import TradingLogger

def test_symbol_info():
    """Тестирование информации о символах"""
    logger = TradingLogger()
    logger.log("=== ТЕСТИРОВАНИЕ ИНФОРМАЦИИ О СИМВОЛАХ ===", 'info')
    
    try:
        symbol_info = SymbolInfo()
        client = BybitClient()
        
        test_symbols = ['SOLUSDT', 'XRPUSDT', 'BTCUSDT', 'ETHUSDT']
        
        for symbol in test_symbols:
            logger.log(f"Тестирование символа: {symbol}", 'info')
            
            # Получаем информацию о символе
            info = symbol_info.get_symbol_info(symbol)
            logger.log(f"Информация о {symbol}: {info}", 'info')
            
            # Получаем текущую цену
            price = client.get_current_price(symbol)
            if price:
                logger.log(f"Текущая цена {symbol}: {price}", 'info')
                
                # Тестируем расчет количества
                test_usdt_amount = 10.0
                quantity = symbol_info.calculate_proper_quantity(symbol, test_usdt_amount, price)
                order_value = quantity * price
                
                logger.log(f"Расчет для {symbol}: {test_usdt_amount} USDT -> {quantity} (стоимость: {order_value:.2f} USDT)", 'info')
                
                # Проверяем валидность
                is_valid, msg = symbol_info.validate_order_quantity(symbol, quantity, price)
                if is_valid:
                    logger.log(f"✅ Расчет для {symbol} ВАЛИДЕН: {msg}", 'info')
                else:
                    logger.log(f"❌ Расчет для {symbol} НЕВАЛИДЕН: {msg}", 'error')
            
            logger.log("---", 'info')
        
        logger.log("=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===", 'info')
        return True
        
    except Exception as e:
        logger.log(f"Ошибка тестирования информации о символах: {e}", 'error')
        return False

if __name__ == "__main__":
    load_dotenv()
    if test_symbol_info():
        print("\n✅ Тестирование информации о символах завершено успешно!")
    else:
        print("\n❌ Тестирование информации о символах выявило проблемы!")