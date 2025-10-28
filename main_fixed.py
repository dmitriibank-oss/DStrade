import time
import schedule
from datetime import datetime
from config.config import Config
from src.bybit_client import BybitClient
from src.trading_strategy import TradingStrategy
from src.risk_manager import RiskManager
from src.logger import TradingLogger

class TradingBot:
    def __init__(self):
        self.client = BybitClient()
        self.strategy = TradingStrategy()
        self.logger = TradingLogger()
        
        # Тестируем подключение при инициализации
        if not self.client.test_connection():
            self.logger.log("Failed to connect to Bybit API. Check your API keys and internet connection.", 'error')
            return
        
        # Инициализация баланса
        initial_balance = self.client.get_account_balance()
        self.risk_manager = RiskManager(initial_balance)
        
        self.active_positions = {}
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0,
            'cycles_completed': 0
        }
        
        self.logger.log(f"Trading bot initialized with balance: {initial_balance} USDT", 'info', True)
    
    def run_trading_cycle(self):
        """Основной торговый цикл"""
        try:
            self.performance_stats['cycles_completed'] += 1
            self.logger.log(f"Starting trading cycle #{self.performance_stats['cycles_completed']}...", 'info')
            
            # Проверка рисков
            if not self.risk_manager.can_trade():
                self.logger.log("Trading paused due to risk management rules", 'warning')
                return
            
            # Обновление баланса
            current_balance = self.client.get_account_balance()
            if current_balance:
                self.risk_manager.update_balance(current_balance)
            
            # Анализ каждого символа
            trades_this_cycle = 0
            for symbol in Config.SYMBOLS:
                if self.analyze_and_trade(symbol):
                    trades_this_cycle += 1
                
                # Небольшая пауза между символами
                time.sleep(1)
            
            self.log_performance()
            
            if trades_this_cycle > 0:
                self.logger.log(f"Executed {trades_this_cycle} trades this cycle", 'info', True)
            
        except Exception as e:
            self.logger.log(f"Error in trading cycle: {e}", 'error')
    
    def analyze_and_trade(self, symbol):
        """Анализ и выполнение торговых операций для символа"""
        try:
            # Получение данных с увеличенным лимитом
            df = self.client.get_klines(symbol, limit=200)
            if df is None or len(df) < 50:
                self.logger.log(f"Not enough data for {symbol}", 'warning')
                return False
            
            # Получение текущей цены
            current_price = self.client.get_current_price(symbol)
            if current_price is None:
                return False
            
            # Анализ стратегии
            signal, details = self.strategy.analyze_symbol(symbol, df)
            
            if signal in ['BUY', 'SELL']:
                self.logger.log(f"Trading signal for {symbol}: {signal} - {details}", 'info')
                
                # Расчет размера позиции (очень маленький для тестирования)
                position_size_usd = min(Config.MAX_POSITION_SIZE, self.risk_manager.current_balance * Config.RISK_PER_TRADE)
                position_size = position_size_usd / current_price
                
                # Минимальный размер позиции для Bybit
                if position_size * current_price < 1:  # Минимум 1 USDT
                    self.logger.log(f"Position size too small for {symbol}: {position_size * current_price:.2f} USDT", 'warning')
                    return False
                
                if position_size > 0:
                    # Размещение ордера
                    side = "Buy" if signal == 'BUY' else "Sell"
                    order = self.client.place_order(symbol, side, position_size)
                    
                    if order:
                        # Расчет SL/TP
                        stop_loss, take_profit = self.risk_manager.calculate_stop_loss_take_profit(
                            current_price, signal
                        )
                        
                        # Запись сделки
                        self.risk_manager.record_trade(
                            symbol, side, current_price, position_size, 
                            stop_loss, take_profit
                        )
                        
                        self.performance_stats['total_trades'] += 1
                        self.logger.log(
                            f"Order executed: {side} {position_size:.6f} {symbol} "
                            f"at {current_price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}",
                            'info', True
                        )
                        return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"Error analyzing/trading {symbol}: {e}", 'error')
            return False
    
    def log_performance(self):
        """Логирование статистики производительности"""
        win_rate = 0
        if self.performance_stats['total_trades'] > 0:
            win_rate = (self.performance_stats['winning_trades'] / 
                       self.performance_stats['total_trades'] * 100)
        
        performance_msg = (
            f"Performance Stats: "
            f"Cycles: {self.performance_stats['cycles_completed']}, "
            f"Total Trades: {self.performance_stats['total_trades']}, "
            f"Win Rate: {win_rate:.1f}%, "
            f"Total PnL: {self.performance_stats['total_pnl']:.2f} USDT, "
            f"Current Balance: {self.risk_manager.current_balance:.2f} USDT, "
            f"Drawdown: {self.risk_manager.calculate_drawdown():.2%}"
        )
        
        self.logger.log(performance_msg, 'info')
    
    def run(self):
        """Запуск бота"""
        self.logger.log("Trading bot started successfully on BYBIT TESTNET!", 'info', True)
        
        # Настройка расписания (реже для тестирования)
        schedule.every(2).minutes.do(self.run_trading_cycle)  # Каждые 2 минуты
        schedule.every(1).hours.do(self.log_performance)
        
        # Первый запуск сразу
        self.run_trading_cycle()
        
        self.logger.log("Bot is running. Press Ctrl+C to stop.", 'info')
        
        # Основной цикл
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.logger.log("Bot stopped by user", 'info', True)
                break
            except Exception as e:
                self.logger.log(f"Unexpected error in main loop: {e}", 'error')
                time.sleep(60)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()