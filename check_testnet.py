import os
import sys
from dotenv import load_dotenv

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import Config

def check_config():
    """Проверка конфигурации"""
    print("=== CONFIGURATION CHECK ===")
    print(f"TESTNET mode: {Config.TESTNET}")
    print(f"API Key present: {bool(Config.BYBIT_API_KEY)}")
    print(f"API Secret present: {bool(Config.BYBIT_API_SECRET)}")
    print(f"Base URL: {'https://api-testnet.bybit.com' if Config.TESTNET else 'https://api.bybit.com'}")
    print(f"Trading symbols: {Config.SYMBOLS}")
    
    # Проверка формата API ключа (тестовые ключи обычно короче)
    if Config.BYBIT_API_KEY:
        print(f"API Key length: {len(Config.BYBIT_API_KEY)}")
        print(f"API Key starts with: {Config.BYBIT_API_KEY[:10]}...")

if __name__ == "__main__":
    load_dotenv()
    check_config()
    