import time
import schedule
from datetime import datetime
from config.config import Config
from src.bybit_client import BybitClient
from src.trading_strategy import TradingStrategy
from src.risk_manager import RiskManager
from src.position_manager import PositionManager
from src.logger import TradingLogger

class ProfessionalTradingBot:
    def __init__(self):
        self.client = BybitClient()
        self.strategy = TradingStrategy()
        self.logger = TradingLogger()
        self.position_manager = PositionManager(self.client)
        
        # Проверка подключения
        if not self.client.test_connection():
            raise Exception("Не удалось подключиться к Bybit API")
        
        # Инициализация баланса и риск-менеджера
        initial_balance = self.client.get_account_balance()
        self.risk_manager = RiskManager(initial_balance)
        
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0,
            'cycles_completed': 0,
            'total_commission': 0
        }
        
        self.max_simultaneous_positions = 3  # Максимум позиций одновременно
        
        self.logger.log(f"Профессиональный торговый бот инициализирован с балансом: {initial_balance} USDT", 'info', True)
    
    def run_trading_cycle(self):
        """Улучшенный торговый цикл"""
        try:
            self.performance_stats['cycles_completed'] += 1
            
            # Обновление баланса
            current_balance = self.client.get_account_balance()
            if current_balance:
                self.risk_manager.update_balance(current_balance)
            
            # Проверка рисков
            if not self.risk_manager.can_trade():
                self.logger.log("Торговля приостановлена по правилам риск-менеджмента", 'warning')
                return
            
            # Мониторинг активных позиций
            self.monitor_active_positions()
            
            # Если достигнут лимит позиций - пропускаем анализ
            if self.position_manager.get_active_positions_count() >= self.max_simultaneous_positions:
                self.logger.log("Достигнут лимит активных позиций", 'info')
                return
            
            # Анализ и торговля
            trades_executed = self.analyze_and_trade()
            
            self.log_performance()
            
        except Exception as e:
            self.logger.log(f"Ошибка в торговом цикле: {e}", 'error')
    
    def analyze_and_trade(self):
        """Улучшенная логика анализа и торговли"""
        trades_executed = 0
        
        for symbol in Config.SYMBOLS:
            try:
                # Получение данных
                df = self.client.get_klines(symbol, limit=200)
                if df is None or len(df) < 50:
                    continue
                
                # Анализ
                signal, details = self.strategy.analyze_symbol(symbol, df)
                current_price = self.client.get_current_price(symbol)
                
                if signal in ['BUY', 'SELL'] and current_price:
                    # Расчет параметров сделки
                    stop_loss, take_profit = self.risk_manager.calculate_stop_loss_take_profit(
                        current_price, signal
                    )
                    
                    # Расчет размера позиции
                    position_size_usdt = min(
                        Config.MAX_POSITION_SIZE,
                        self.risk_manager.current_balance * Config.RISK_PER_TRADE
                    )
                    position_size = position_size_usdt / current_price
                    
                    # Проверка минимального размера
                    is_valid, validation_msg = self.risk_manager.validate_trade_size(
                        symbol, position_size_usdt
                    )
                    if not is_valid:
                        self.logger.log(f"Пропуск сделки {symbol}: {validation_msg}", 'info')
                        continue
                    
                    # Проверка прибыльности с учетом комиссий
                    is_profitable, net_profit, commission = self.risk_manager.is_trade_profitable(
                        symbol, current_price, position_size, take_profit
                    )
                    
                    if not is_profitable:
                        self.logger.log(f"Пропуск сделки {symbol}: не покрывает комиссии", 'info')
                        continue
                    
                    # Открытие позиции
                    if self.position_manager.open_position(
                        symbol, signal, position_size, current_price, stop_loss, take_profit
                    ):
                        trades_executed += 1
                        self.performance_stats['total_trades'] += 1
                        self.performance_stats['total_commission'] += commission
                        
                        # Пауза между сделками
                        time.sleep(1)
                
            except Exception as e:
                self.logger.log(f"Ошибка анализа {symbol}: {e}", 'error')
        
        return trades_executed
    
    def monitor_active_positions(self):
        """Мониторинг активных позиций"""
        for symbol in list(self.position_manager.active_positions.keys()):
            try:
                current_price = self.client.get_current_price(symbol)
                if not current_price:
                    continue
                
                position = self.position_manager.active_positions[symbol]
                
                # Проверка стоп-лосса и тейк-профита
                if (position['side'] == 'Buy' and current_price <= position['stop_loss']) or \
                   (position['side'] == 'Sell' and current_price >= position['stop_loss']):
                    self.position_manager.close_position(symbol, "Stop Loss")
                
                elif (position['side'] == 'Buy' and current_price >= position['take_profit']) or \
                     (position['side'] == 'Sell' and current_price <= position['take_profit']):
                    self.position_manager.close_position(symbol, "Take Profit")
                
                # Проверка здоровья позиции
                self.position_manager.check_position_health(symbol, current_price)
                
            except Exception as e:
                self.logger.log(f"Ошибка мониторинга позиции {symbol}: {e}", 'error')
    
    def log_performance(self):
        """Детальное логирование производительности"""
        win_rate = 0
        if self.performance_stats['total_trades'] > 0:
            win_rate = (self.performance_stats['winning_trades'] / 
                       self.performance_stats['total_trades'] * 100)
        
        avg_commission = 0
        if self.performance_stats['total_trades'] > 0:
            avg_commission = self.performance_stats['total_commission'] / self.performance_stats['total_trades']
        
        performance_msg = (
            f"Производительность: "
            f"Циклы: {self.performance_stats['cycles_completed']} | "
            f"Сделки: {self.performance_stats['total_trades']} | "
            f"Винрейт: {win_rate:.1f}% | "
            f"Общий PnL: {self.performance_stats['total_pnl']:.2f} USDT | "
            f"Комиссии: {self.performance_stats['total_commission']:.2f} USDT | "
            f"Баланс: {self.risk_manager.current_balance:.2f} USDT"
        )
        
        self.logger.log(performance_msg, 'info')
    
    def run(self):
        """Запуск бота"""
        self.logger.log("🚀 ПРОФЕССИОНАЛЬНЫЙ ТОРГОВЫЙ БOT ЗАПУЩЕН!", 'info', True)
        
        # Настройка расписания
        schedule.every(2).minutes.do(self.run_trading_cycle)
        schedule.every(30).minutes.do(self.log_performance)
        
        # Запуск первого цикла
        self.run_trading_cycle()
        
        self.logger.log("Бот работает. Ctrl+C для остановки.", 'info')
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.logger.log("Бот остановлен пользователем", 'info', True)
                break
            except Exception as e:
                self.logger.log(f"Неожиданная ошибка: {e}", 'error')
                time.sleep(60)

if __name__ == "__main__":
    try:
        bot = ProfessionalTradingBot()
        bot.run()
    except Exception as e:
        logger = TradingLogger()
        logger.log(f"Критическая ошибка запуска: {e}", 'error', True)