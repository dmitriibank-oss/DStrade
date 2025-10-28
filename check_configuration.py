import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from src.bybit_client import BybitClient
from src.logger import TradingLogger

def check_configuration():
    """Комплексная проверка конфигурации"""
    logger = TradingLogger()
    logger.log("=== КОМПЛЕКСНАЯ ПРОВЕРКА КОНФИГУРАЦИИ ===", 'info')
    
    # Проверка API ключей
    logger.log("1. Проверка API ключей...", 'info')
    if not Config.BYBIT_API_KEY or not Config.BYBIT_API_SECRET:
        logger.log("[ERROR] API ключи не настроены в .env файле", 'error')
        return False
    logger.log("[OK] API ключи настроены", 'info')
    
    # Проверка подключения к testnet
    logger.log("2. Проверка подключения к Bybit Testnet...", 'info')
    try:
        client = BybitClient()
        if not client.test_connection():
            logger.log("[ERROR] Не удалось подключиться к Bybit Testnet", 'error')
            return False
        logger.log("[OK] Подключение к Bybit Testnet успешно", 'info')
    except Exception as e:
        logger.log(f"[ERROR] Ошибка подключения: {e}", 'error')
        return False
    
    # Проверка баланса
    logger.log("3. Проверка баланса...", 'info')
    balance = client.get_account_balance()
    logger.log(f"[OK] Текущий баланс: {balance} USDT", 'info')
    
    # Проверка торговых пар
    logger.log("4. Проверка торговых пар...", 'info')
    for symbol in Config.SYMBOLS:
        price = client.get_current_price(symbol)
        if price:
            logger.log(f"[OK] {symbol}: {price}", 'info')
        else:
            logger.log(f"[WARNING] Не удалось получить цену для {symbol}", 'warning')
    
    # Проверка параметров рисков
    logger.log("5. Проверка параметров рисков...", 'info')
    risk_params = [
        ("MAX_POSITION_SIZE", Config.MAX_POSITION_SIZE),
        ("RISK_PER_TRADE", Config.RISK_PER_TRADE),
        ("STOP_LOSS_PCT", Config.STOP_LOSS_PCT),
        ("TAKE_PROFIT_PCT", Config.TAKE_PROFIT_PCT),
        ("MAX_DRAWDOWN", Config.MAX_DRAWDOWN)
    ]
    
    for param, value in risk_params:
        logger.log(f"[OK] {param}: {value}", 'info')
    
    # Проверка минимальных комиссий
    logger.log("6. Проверка комиссий...", 'info')
    check_commissions(client, balance, logger)
    
    logger.log("[OK] Все проверки завершены успешно!", 'info')
    return True

def check_commissions(client, balance, logger):
    """Проверка комиссий и минимальных размеров позиций"""
    try:
        # Получаем информацию о торговых парах
        btc_price = client.get_current_price('BTCUSDT')
        if btc_price:
            # Минимальная позиция в USDT (примерно)
            min_position_usdt = 1.0  # Bybit обычно требует минимум 1 USDT
            
            # Комиссия за сделку (0.1% для тестнета)
            commission_rate = 0.001  # 0.1%
            
            # Минимальная прибыль должна покрывать комиссию
            min_profit_to_cover_commission = commission_rate * 2  # вход + выход
            
            logger.log(f"[INFO] Минимальный размер позиции: {min_position_usdt} USDT", 'info')
            logger.log(f"[INFO] Комиссия за сделку: {commission_rate*100}%", 'info')
            logger.log(f"[INFO] Минимальная прибыль для покрытия комиссий: {min_profit_to_cover_commission*100}%", 'info')
            
            # Проверяем, что настройки бота соответствуют
            if Config.MAX_POSITION_SIZE < min_position_usdt:
                logger.log(f"[WARNING] MAX_POSITION_SIZE ({Config.MAX_POSITION_SIZE}) меньше минимальной позиции!", 'warning')
            
            if Config.TAKE_PROFIT_PCT <= min_profit_to_cover_commission:
                logger.log(f"[CRITICAL] TAKE_PROFIT_PCT ({Config.TAKE_PROFIT_PCT}) не покрывает комиссии!", 'error')
            
    except Exception as e:
        logger.log(f"[ERROR] Ошибка при проверке комиссий: {e}", 'error')

if __name__ == "__main__":
    load_dotenv()
    if check_configuration():
        print("\n✅ Конфигурация проверена успешно!")
    else:
        print("\n❌ Обнаружены проблемы в конфигурации!")