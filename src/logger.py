import logging
import requests
import json
import sys
from config.config import Config

class TradingLogger:
    def __init__(self):
        self.logger = logging.getLogger('trading_bot')
        
        # Проверяем, не были ли уже добавлены обработчики
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            
            # File handler
            fh = logging.FileHandler('trading_bot.log', encoding='utf-8')
            fh.setLevel(logging.INFO)
            
            # Console handler с правильной кодировкой для Windows
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
        
        self.telegram_enabled = bool(Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID)
    
    def _send_telegram_sync(self, message):
        """Синхронная отправка сообщения в Telegram"""
        try:
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': Config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Failed to send Telegram message: {e}")
            return False
    
    def log(self, message, level='info', send_telegram=False):
        # Заменяем Unicode символы на текстовые для Windows
        message = message.replace('✓', '[OK]').replace('✗', '[ERROR]')
        
        if level == 'info':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'error':
            self.logger.error(message)
        
        if send_telegram and self.telegram_enabled:
            self._send_telegram_sync(message)