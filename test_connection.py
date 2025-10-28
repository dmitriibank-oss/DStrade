import os
import sys
from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.bybit_client import BybitClient
from src.logger import TradingLogger

def test_connection_v5():
    """Тестирование подключения к Bybit API v5"""
    logger = TradingLogger()
    logger.log("Testing connection to Bybit API v5...", 'info')
    
    try:
        client = BybitClient()
        
        # Тест времени сервера
        server_time = client.get_server_time()
        if server_time:
            logger.log(f"Server time: {server_time}", 'info')
        else:
            logger.log("Failed to get server time", 'error')
        
        # Тест баланса
        balance = client.get_account_balance()
        logger.log(f"Balance: {balance}", 'info')
        
        # Тест цен
        symbols = ['BTCUSDT', 'ETHUSDT']
        for symbol in symbols:
            price = client.get_current_price(symbol)
            if price:
                logger.log(f"Price for {symbol}: {price}", 'info')
            else:
                logger.log(f"Failed to get price for {symbol}", 'error')
        
        # Тест исторических данных
        data = client.get_klines('BTCUSDT', limit=10)
        if data is not None:
            logger.log(f"Klines test: Got {len(data)} rows", 'info')
            logger.log(f"Latest close price: {data['close'].iloc[-1]}", 'info')
        else:
            logger.log("Failed to get klines data", 'error')
            
    except Exception as e:
        logger.log(f"Connection test failed: {e}", 'error')

if __name__ == "__main__":
    test_connection_v5()