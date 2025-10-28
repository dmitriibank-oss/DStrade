from src.bybit_client import BybitClient
from src.logger import TradingLogger

class SymbolInfo:
    def __init__(self):
        self.client = BybitClient()
        self.logger = TradingLogger()
        self.symbol_info_cache = {}
    
    def _round_to_step(self, quantity, step):
        """Округление количества до шага с учетом проблем с float"""
        if step <= 0:
            return quantity
        
        # Определяем количество знаков после запятой для шага
        step_str = str(step)
        if '.' in step_str:
            decimal_places = len(step_str.split('.')[1])
        else:
            decimal_places = 0
        
        # Округляем до шага
        rounded_quantity = round(quantity / step) * step
        # Округляем до нужного количества знаков, чтобы избежать проблем с float
        rounded_quantity = round(rounded_quantity, decimal_places)
        
        return rounded_quantity
    
    def get_symbol_info(self, symbol):
        """Получение информации о символе (минимальные размеры и т.д.)"""
        if symbol in self.symbol_info_cache:
            return self.symbol_info_cache[symbol]
        
        try:
            response = self.client._make_request('GET', '/v5/market/instruments-info', {
                'category': 'linear',
                'symbol': symbol
            })
            
            if response and 'result' in response and 'list' in response['result']:
                instruments = response['result']['list']
                if instruments and len(instruments) > 0:
                    instrument = instruments[0]
                    lot_filter = instrument.get('lotSizeFilter', {})
                    info = {
                        'min_order_qty': float(lot_filter.get('minOrderQty', 0)),
                        'max_order_qty': float(lot_filter.get('maxOrderQty', 0)),
                        'qty_step': float(lot_filter.get('qtyStep', 0.001)),
                        'min_order_value': float(lot_filter.get('minOrderAmt', 5.0)),
                    }
                    self.symbol_info_cache[symbol] = info
                    self.logger.log(f"Symbol info for {symbol}: min_qty={info['min_order_qty']}, qty_step={info['qty_step']}, min_value={info['min_order_value']}", 'info')
                    return info
            
            # Возвращаем значения по умолчанию, если не удалось получить информацию
            default_info = self._get_default_symbol_info(symbol)
            self.symbol_info_cache[symbol] = default_info
            return default_info
            
        except Exception as e:
            self.logger.log(f"Error getting symbol info for {symbol}: {e}", 'error')
            default_info = self._get_default_symbol_info(symbol)
            self.symbol_info_cache[symbol] = default_info
            return default_info
    
    def _get_default_symbol_info(self, symbol):
        """Значения по умолчанию для популярных символов"""
        default_info = {
            'min_order_qty': 0.001,
            'max_order_qty': 1000000,
            'qty_step': 0.001,
            'min_order_value': 5.0,
        }
        
        # Специфичные настройки для известных символов
        symbol_specific = {
            'BTCUSDT': {'min_order_qty': 0.001, 'qty_step': 0.001},
            'ETHUSDT': {'min_order_qty': 0.01, 'qty_step': 0.01},
            'SOLUSDT': {'min_order_qty': 0.1, 'qty_step': 0.1},
            'XRPUSDT': {'min_order_qty': 0.1, 'qty_step': 0.1},
            'ADAUSDT': {'min_order_qty': 1.0, 'qty_step': 0.1},
            'DOTUSDT': {'min_order_qty': 0.1, 'qty_step': 0.1},
            'LINKUSDT': {'min_order_qty': 0.1, 'qty_step': 0.1},
        }
        
        if symbol in symbol_specific:
            default_info.update(symbol_specific[symbol])
        
        return default_info
    
    def validate_order_quantity(self, symbol, quantity, price):
        """Проверка валидности размера ордера"""
        info = self.get_symbol_info(symbol)
        
        # Округляем количество до шага для проверки
        step = info['qty_step']
        rounded_quantity = self._round_to_step(quantity, step)
        
        # Проверяем, что округленное количество близко к исходному (допуск 0.0001)
        if abs(quantity - rounded_quantity) > 0.0001:
            return False, f"Quantity {quantity} is not a multiple of step {step}"
        
        # Проверка минимального количества
        if rounded_quantity < info['min_order_qty']:
            return False, f"Quantity {rounded_quantity} is less than minimum {info['min_order_qty']}"
        
        # Проверка минимальной стоимости
        order_value = rounded_quantity * price
        if order_value < info['min_order_value']:
            return False, f"Order value {order_value:.2f} USDT is less than minimum {info['min_order_value']} USDT"
        
        return True, "Valid"
    
    def calculate_proper_quantity(self, symbol, desired_usdt_amount, price):
        """Расчет правильного количества с учетом ограничений символа"""
        info = self.get_symbol_info(symbol)
        step = info['qty_step']
        
        # Базовая расчетная quantity
        base_quantity = desired_usdt_amount / price
        
        # Округляем до шага
        quantity = self._round_to_step(base_quantity, step)
        
        # Проверяем минимальное количество
        if quantity < info['min_order_qty']:
            quantity = info['min_order_qty']
            # Пересчитываем с минимальным количеством
            quantity = self._round_to_step(quantity, step)
        
        # Проверяем минимальную стоимость
        order_value = quantity * price
        if order_value < info['min_order_value']:
            # Рассчитываем минимальное количество для минимальной стоимости
            min_quantity = info['min_order_value'] / price
            quantity = self._round_to_step(min_quantity, step)
            
            # Проверяем, что не меньше минимального количества
            if quantity < info['min_order_qty']:
                quantity = info['min_order_qty']
                quantity = self._round_to_step(quantity, step)
        
        # Проверяем максимальное количество (на всякий случай)
        if quantity > info['max_order_qty']:
            quantity = info['max_order_qty']
            quantity = self._round_to_step(quantity, step)
        
        final_value = quantity * price
        self.logger.log(f"Calculated quantity for {symbol}: {quantity} (value: {final_value:.2f} USDT)", 'info')
        
        return quantity