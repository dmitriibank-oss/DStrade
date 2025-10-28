from config.config import Config
from src.logger import TradingLogger
from datetime import datetime

class RiskManager:
    def __init__(self, initial_balance):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.logger = TradingLogger()
        self.trades = []
        self.commission_rate = 0.001  # 0.1% комиссия Bybit
        self.min_position_usdt = 1.0
        
        # Daily limits
        self.daily_start_balance = initial_balance
        self.daily_loss_limit = getattr(Config, 'DAILY_LOSS_LIMIT', 0.03)  # Запасной вариант
        self.last_reset_date = datetime.now().date()
    
    def _reset_daily_limits(self):
        """Сброс дневных лимитов при смене дня"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_start_balance = self.current_balance
            self.trades = []
            self.last_reset_date = current_date
            self.logger.log("Daily limits reset", 'info')
    
    def update_balance(self, new_balance):
        """Обновление баланса и отслеживание просадки"""
        self.current_balance = new_balance
        self.peak_balance = max(self.peak_balance, new_balance)
        self._reset_daily_limits()
    
    def calculate_drawdown(self):
        """Расчет текущей просадки"""
        if self.peak_balance == 0:
            return 0
        return (self.peak_balance - self.current_balance) / self.peak_balance
    
    def calculate_daily_pnl(self):
        """Расчет дневного PnL"""
        return (self.current_balance - self.daily_start_balance) / self.daily_start_balance
    
    def can_trade(self):
        """Проверка возможности торговли по рискам"""
        # Максимальная просадка
        drawdown = self.calculate_drawdown()
        if drawdown > Config.MAX_DRAWDOWN:
            self.logger.log(f"Торговля остановлена: превышена максимальная просадка ({drawdown:.2%})", 'warning', True)
            return False
        
        # Дневной лимит убытков
        daily_pnl = self.calculate_daily_pnl()
        if daily_pnl < -self.daily_loss_limit:
            self.logger.log(f"Торговля остановлена: превышен дневной лимит убытков ({daily_pnl:.2%})", 'warning', True)
            return False
        
        # Минимальный баланс
        if self.current_balance < self.initial_balance * 0.3:
            self.logger.log("Торговля остановлена: баланс ниже 30% от начального", 'warning', True)
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
        
        # Проверка на слишком большие позиции
        if position_size_usdt > self.current_balance * 0.2:  # Больше 20% от баланса
            return False, f"Размер позиции слишком велик относительно баланса"
            
        return True, "OK"
    
    def record_trade(self, symbol, side, entry_price, quantity, stop_loss, take_profit, pnl=0):
        """Запись информации о сделке"""
        trade = {
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pnl': pnl,
            'timestamp': datetime.now().isoformat(),
            'balance_after': self.current_balance
        }
        self.trades.append(trade)
    
    def get_performance_metrics(self):
        """Получение метрик производительности"""
        if not self.trades:
            return {}
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'drawdown': self.calculate_drawdown()
        }