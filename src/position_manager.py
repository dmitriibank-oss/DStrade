import time
from config.config import Config
from src.logger import TradingLogger

class PositionManager:
    def __init__(self, bybit_client):
        self.client = bybit_client
        self.logger = TradingLogger()
        self.active_positions = {}
    
    def open_position(self, symbol, side, quantity, entry_price, stop_loss, take_profit):
        """Открытие позиции с управлением рисками"""
        try:
            # Проверяем, нет ли уже активной позиции
            if symbol in self.active_positions:
                self.logger.log(f"Позиция для {symbol} уже открыта", 'warning')
                return False
            
            # Размещаем ордер
            order = self.client.place_order(symbol, side, quantity)
            
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
                self.logger.log(f"Позиция открыта: {side} {quantity:.6f} {symbol} по цене {entry_price}", 'info', True)
                return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"Ошибка открытия позиции: {e}", 'error')
            return False
    
    def check_position_health(self, symbol, current_price):
        """Проверка здоровья позиции"""
        if symbol not in self.active_positions:
            return True
        
        position = self.active_positions[symbol]
        entry_price = position['entry_price']
        
        # Расчет текущего PnL
        if position['side'] == 'Buy':
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price
        
        # Логирование состояния позиции каждые 2%
        if abs(pnl_pct) > 0.02 and abs(pnl_pct) % 0.02 < 0.005:
            self.logger.log(f"Позиция {symbol}: PnL {pnl_pct:+.2%}", 'info')
        
        return True
    
    def close_position(self, symbol, reason=""):
        """Закрытие позиции"""
        try:
            if symbol not in self.active_positions:
                self.logger.log(f"Нет активной позиции для {symbol}", 'warning')
                return False
            
            position = self.active_positions[symbol]
            
            # Определяем сторону для закрытия
            close_side = "Sell" if position['side'] == "Buy" else "Buy"
            
            # Размещаем ордер на закрытие
            order = self.client.place_order(
                symbol, 
                close_side, 
                position['quantity']
            )
            
            if order:
                # Расчет PnL
                current_price = self.client.get_current_price(symbol)
                if current_price:
                    if position['side'] == 'Buy':
                        pnl = (current_price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - current_price) * position['quantity']
                    
                    self.logger.log(
                        f"Позиция закрыта: {symbol} | PnL: {pnl:+.2f} USDT | Причина: {reason}",
                        'info', 
                        True
                    )
                
                del self.active_positions[symbol]
                return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"Ошибка закрытия позиции: {e}", 'error')
            return False
    
    def get_active_positions_count(self):
        """Получение количества активных позиций"""
        return len(self.active_positions)