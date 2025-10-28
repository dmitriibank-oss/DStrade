import time
from config.config import Config
from src.logger import TradingLogger

class PositionManager:
    def __init__(self, bybit_client):
        self.client = bybit_client
        self.logger = TradingLogger()
        self.active_positions = {}
    
    def sync_positions(self):
        """Упрощенная синхронизация позиций"""
        try:
            real_positions = self.client.get_open_positions()
            real_symbols = {pos['symbol'] for pos in real_positions}
            
            # Удаляем позиции, которых нет на бирже
            for symbol in list(self.active_positions.keys()):
                if symbol not in real_symbols:
                    self.logger.log(f"Позиция {symbol} закрыта на бирже", 'info')
                    del self.active_positions[symbol]
            
        except Exception as e:
            self.logger.log(f"Ошибка синхронизации позиций: {e}", 'error')
    
    def can_open_position(self, symbol):
        """Проверка возможности открытия позиции"""
        self.sync_positions()
        
        if len(self.active_positions) >= Config.MAX_POSITIONS:
            return False, f"Достигнут лимит позиций ({Config.MAX_POSITIONS})"
        
        if symbol in self.active_positions:
            return False, "Позиция уже открыта"
            
        return True, "OK"
    
    def open_position(self, symbol, side, quantity, entry_price, stop_loss, take_profit):
        """Открытие позиции"""
        try:
            can_open, reason = self.can_open_position(symbol)
            if not can_open:
                return False
            
            # Используем лимитные ордера
            order_type = "Limit"
            price = None
            
            if Config.USE_LIMIT_ORDERS:
                if side == "BUY":
                    price = entry_price * (1 - Config.LIMIT_ORDER_PRICE_OFFSET)
                else:
                    price = entry_price * (1 + Config.LIMIT_ORDER_PRICE_OFFSET)
            
            order = self.client.place_order(symbol, side, quantity, order_type, price)
            
            if order:
                position = {
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'order_id': order.get('result', {}).get('orderId', 'N/A'),
                    'timestamp': time.time()
                }
                
                self.active_positions[symbol] = position
                self.logger.log(f"✅ ПОЗИЦИЯ ОТКРЫТА: {side} {quantity:.4f} {symbol}", 'info', True)
                return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"Ошибка открытия позиции: {e}", 'error')
            return False
    
    def get_active_positions_count(self):
        """Получение количества активных позиций"""
        self.sync_positions()
        return len(self.active_positions)