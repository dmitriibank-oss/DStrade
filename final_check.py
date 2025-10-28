import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def final_system_check():
    """Финальная проверка всей системы"""
    print("=== ФИНАЛЬНАЯ ПРОВЕРКА СИСТЕМЫ ===")
    
    # Проверка конфигурации
    from config.config import Config
    print("1. Проверка конфигурации...")
    if not Config.BYBIT_API_KEY or not Config.BYBIT_API_SECRET:
        print("❌ API ключи не настроены")
        return False
    print("✅ Конфигурация OK")
    
    # Проверка подключения
    print("2. Проверка подключения к Bybit...")
    from src.bybit_client import BybitClient
    try:
        client = BybitClient()
        if not client.test_connection():
            print("❌ Не удалось подключиться к Bybit")
            return False
        print("✅ Подключение к Bybit OK")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False
    
    # Проверка баланса
    print("3. Проверка баланса...")
    try:
        balance = client.get_account_balance()
        print(f"✅ Баланс: {balance} USDT")
    except Exception as e:
        print(f"❌ Ошибка получения баланса: {e}")
        return False
    
    # Проверка информации о символах
    print("4. Проверка информации о символах...")
    from src.symbol_info import SymbolInfo
    try:
        symbol_info = SymbolInfo()
        test_symbols = ['SOLUSDT', 'XRPUSDT']
        for symbol in test_symbols:
            info = symbol_info.get_symbol_info(symbol)
            print(f"✅ {symbol}: min_qty={info['min_order_qty']}, min_value={info['min_order_value']} USDT")
    except Exception as e:
        print(f"❌ Ошибка информации о символах: {e}")
        return False
    
    # Проверка расчета позиций
    print("5. Проверка расчета позиций...")
    try:
        for symbol in test_symbols:
            price = client.get_current_price(symbol)
            if price:
                quantity = symbol_info.calculate_proper_quantity(symbol, 10.0, price)
                is_valid, msg = symbol_info.validate_order_quantity(symbol, quantity, price)
                if is_valid:
                    print(f"✅ {symbol}: расчет OK ({quantity} = {quantity * price:.2f} USDT)")
                else:
                    print(f"❌ {symbol}: расчет невалиден - {msg}")
                    return False
    except Exception as e:
        print(f"❌ Ошибка расчета позиций: {e}")
        return False
    
    print("=== ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО! ===")
    print("🎉 Система готова к работе!")
    print("\nЗапустите: python simple_professional_bot.py")
    return True

if __name__ == "__main__":
    load_dotenv()
    if final_system_check():
        print("\n✅ Система полностью готова к работе!")
    else:
        print("\n❌ Обнаружены проблемы в системе!")
        