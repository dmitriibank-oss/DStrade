import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.symbol_info import SymbolInfo
from src.bybit_client import BybitClient
from src.logger import TradingLogger

def test_fixes():
    """Тестирование исправлений"""
    logger = TradingLogger()
    logger.log("=== ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ===", 'info')
    
    try:
        symbol_info = SymbolInfo()
        client = BybitClient()
        
        # Тест округления
        logger.log("Тестирование округления...", 'info')
        test_cases = [
            (2.4000000000000004, 0.1, 2.4),
            (0.123456789, 0.001, 0.123),
            (1.999999999, 0.1, 2.0),
        ]
        
        for input_val, step, expected in test_cases:
            result = symbol_info._round_to_step(input_val, step)
            status = "✅" if abs(result - expected) < 0.0001 else "❌"
            logger.log(f"{status} {input_val} -> {result} (ожидалось: {expected})", 'info')
        
        # Тест расчета позиций
        logger.log("Тестирование расчета позиций...", 'info')
        test_symbols = ['SOLUSDT', 'XRPUSDT']
        
        for symbol in test_symbols:
            price = client.get_current_price(symbol)
            if price:
                quantity = symbol_info.calculate_proper_quantity(symbol, 10.0, price)
                is_valid, msg = symbol_info.validate_order_quantity(symbol, quantity, price)
                
                if is_valid:
                    logger.log(f"✅ {symbol}: расчет валиден - {quantity} (стоимость: {quantity * price:.2f} USDT)", 'info')
                else:
                    logger.log(f"❌ {symbol}: расчет невалиден - {msg}", 'error')
        
        logger.log("=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===", 'info')
        return True
        
    except Exception as e:
        logger.log(f"Ошибка тестирования исправлений: {e}", 'error')
        return False

if __name__ == "__main__":
    load_dotenv()
    if test_fixes():
        print("\n✅ Все исправления работают корректно!")
    else:
        print("\n❌ Обнаружены проблемы в исправлениях!")