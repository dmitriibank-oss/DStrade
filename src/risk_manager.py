from config.config import Config
from src.logger import TradingLogger

class RiskManager:
    def __init__(self, initial_balance):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.logger = TradingLogger()
        self.trades = []
        self.commission_rate = 0.001  # 0.1% комиссия Bybit
        self.min_position_usdt = 1.0  # Минимальная позиция
    
    def update_balance(self, new_balance):
        """Обновление баланса и отслеживание просадки"""
        self.current_balance = new_balance
        self.peak_balance = max(self.peak_balance, new_balance)
    
    def calculate_drawdown(self):
        """Расчет текущей просадки"""
        if self.peak_balance == 0:
            return 0
        return (self.peak_balance - self.current_balance) / self.peak_balance
    
    def can_trade(self):
        """Проверка возможности торговли по рискам"""
        drawdown = self.calculate_drawdown()
        
        if drawdown > Config.MAX_DRAWDOWN:
            self.logger.log(f"Торговля остановлена: превышена максимальная просадка ({drawdown:.2%})", 'warning', True)
            return False
        
        if self.current_balance < self.initial_balance * 0.5:
            self.logger.log("Торговля остановлена: баланс ниже 50% от начального", 'warning', True)
            return False
        
        return True
    
    def calculate_stop_loss_take_profit(self, entry_price, signal_type):
        """Расчет уровней стоп-лосса и тейк-профита"""
        if signal_type == 'BUY':
            stop_loss = entry_price * (1 - Config.STOP_LOSS_PCT)
            take_profit = entry_price * (1 + Config.TAKE_PROFIT_PCT)
        else:  # SELL
            stop_loss = entry_price * (1 + Config.STOP_LOSS_PCT)
            take_profit = entry_price * (1 - Config.TAKE_PROFIT_PCT)
        
        return stop_loss, take_profit
    
    def calculate_min_profitable_trade(self, symbol, position_size_usdt):
        """Расчет минимальной прибыльной сделки с учетом комиссий"""
        # Комиссия за вход и выход
        total_commission = position_size_usdt * self.commission_rate * 2
        
        # Минимальная прибыль должна покрывать комиссию + небольшой запас
        min_profit = total_commission * 1.5  # 50% запас
        
        # Минимальный тейк-профит в процентах
        min_take_profit_pct = min_profit / position_size_usdt
        
        return min_take_profit_pct
    
    def is_trade_profitable(self, symbol, entry_price, position_size, take_profit_price):
        """Проверка, будет ли сделка прибыльной после комиссий"""
        position_value = entry_price * position_size
        
        # Комиссии за вход и выход
        entry_commission = position_value * self.commission_rate
        exit_commission = (take_profit_price * position_size) * self.commission_rate
        total_commission = entry_commission + exit_commission
        
        # Прибыль до комиссий
        if entry_price < take_profit_price:  # LONG
            gross_profit = (take_profit_price - entry_price) * position_size
        else:  # SHORT
            gross_profit = (entry_price - take_profit_price) * position_size
        
        # Чистая прибыль
        net_profit = gross_profit - total_commission
        
        return net_profit > 0, net_profit, total_commission
    
    def validate_trade_size(self, symbol, position_size_usdt):
        """Проверка размера позиции"""
        if position_size_usdt < self.min_position_usdt:
            return False, f"Размер позиции {position_size_usdt:.2f} USDT меньше минимального {self.min_position_usdt} USDT"
        
        # Проверка на слишком маленькие позиции относительно баланса
        if position_size_usdt < self.current_balance * 0.005:  # Меньше 0.5% от баланса
            return False, f"Размер позиции слишком мал относительно баланса"
            
        return True, "OK"
    
    def record_trade(self, symbol, side, entry_price, quantity, stop_loss, take_profit):
        """Запись информации о сделке"""
        trade = {
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        self.trades.append(trade)