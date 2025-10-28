import time
import schedule
from datetime import datetime
from config.config import Config
from src.bybit_client import BybitClient
from src.trading_strategy import TradingStrategy
from src.risk_manager import RiskManager
from src.position_manager import PositionManager
from src.symbol_info import SymbolInfo
from src.logger import TradingLogger

class ProfessionalTradingBot:
    def __init__(self):
        self.client = BybitClient()
        self.strategy = TradingStrategy()
        self.logger = TradingLogger()
        self.symbol_info = SymbolInfo()
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
            'total_commission': 0,
            'rejected_trades': 0
        }
        
        self.max_simultaneous_positions = 2  # Максимум позиций одновременно
        self.min_trade_interval = 60  # Минимальный интервал между сделками (секунды)
        self.last_trade_time = 0
        
        self.logger.log(f"Профессиональный торговый бот инициализирован с балансом: {initial_balance} USDT", 'info', True)
    
    def run_trading_cycle(self):
        """Улучшенный торговый цикл"""
        try:
            self.performance_stats['cycles_completed'] += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.log(f"Запуск цикла #{self.performance_stats['cycles_completed']} в {current_time}", 'info')
            
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
            active_positions_count = self.position_manager.get_active_positions_count()
            if active_positions_count >= self.max_simultaneous_positions:
                self.logger.log(f"Достигнут лимит активных позиций: {active_positions_count}/{self.max_simultaneous_positions}", 'info')
                return
            
            # Проверка временного интервала между сделками
            current_time_seconds = time.time()
            if current_time_seconds - self.last_trade_time < self.min_trade_interval:
                remaining = self.min_trade_interval - (current_time_seconds - self.last_trade_time)
                self.logger.log(f"Слишком рано для новой сделки. Ждем {remaining:.0f} секунд", 'info')
                return
            
            # Анализ и торговля
            trades_executed = self.analyze_and_trade()
            
            if trades_executed > 0:
                self.last_trade_time = current_time_seconds
            
            self.log_performance()
            
        except Exception as e:
            self.logger.log(f"Ошибка в торговом цикле: {e}", 'error')
    
    def analyze_and_trade(self):
        """Улучшенная логика анализа и торговли"""
        trades_executed = 0
        
        for symbol in Config.SYMBOLS:
            try:
                # Пропускаем символы с активными позициями
                if symbol in self.position_manager.active_positions:
                    continue
                
                # Получение данных
                df = self.client.get_klines(symbol, limit=200)
                if df is None or len(df) < 50:
                    self.logger.log(f"Недостаточно данных для {symbol}", 'info')
                    continue
                
                # Анализ
                signal, details = self.strategy.analyze_symbol(symbol, df)
                current_price = self.client.get_current_price(symbol)
                
                if signal in ['BUY', 'SELL'] and current_price:
                    self.logger.log(f"Торговый сигнал для {symbol}: {signal} - {details}", 'info')
                    
                    # Расчет параметров сделки
                    stop_loss, take_profit = self.risk_manager.calculate_stop_loss_take_profit(
                        current_price, signal
                    )
                    
                    # Расчет размера позиции (2% риска от баланса)
                    risk_amount = self.risk_manager.current_balance * Config.RISK_PER_TRADE
                    position_size_usdt = min(Config.MAX_POSITION_SIZE, risk_amount)
                    position_size = self.symbol_info.calculate_proper_quantity(symbol, position_size_usdt, current_price)
                    
                    # Проверка минимального размера
                    is_valid, validation_msg = self.risk_manager.validate_trade_size(
                        symbol, position_size_usdt
                    )
                    if not is_valid:
                        self.performance_stats['rejected_trades'] += 1
                        self.logger.log(f"Пропуск сделки {symbol}: {validation_msg}", 'info')
                        continue
                    
                    # Проверка прибыльности с учетом комиссий
                    is_profitable, net_profit, commission = self.risk_manager.is_trade_profitable(
                        symbol, current_price, position_size, take_profit
                    )
                    
                    if not is_profitable:
                        self.performance_stats['rejected_trades'] += 1
                        self.logger.log(f"Пропуск сделки {symbol}: не покрывает комиссии (чистая прибыль: {net_profit:.4f} USDT)", 'info')
                        continue
                    
                    # Дополнительная проверка: минимальный ожидаемый доход
                    min_acceptable_profit = commission * 2  # Прибыль должна быть как минимум в 2 раза больше комиссии
                    if net_profit < min_acceptable_profit:
                        self.performance_stats['rejected_trades'] += 1
                        self.logger.log(f"Пропуск сделки {symbol}: ожидаемая прибыль слишком мала ({net_profit:.4f} USDT)", 'info')
                        continue
                    
                    # Открытие позиции
                    if self.position_manager.open_position(
                        symbol, signal, position_size, current_price, stop_loss, take_profit
                    ):
                        trades_executed += 1
                        self.performance_stats['total_trades'] += 1
                        self.performance_stats['total_commission'] += commission
                        
                        # Пауза между сделками
                        time.sleep(2)
                
            except Exception as e:
                self.logger.log(f"Ошибка анализа {symbol}: {e}", 'error')
        
        return trades_executed
    
    def monitor_active_positions(self):
        """Мониторинг активных позиций"""
        if not self.position_manager.active_positions:
            return
            
        self.logger.log(f"Мониторинг {len(self.position_manager.active_positions)} активных позиций...", 'info')
        
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
                    self.performance_stats['losing_trades'] += 1
                
                elif (position['side'] == 'Buy' and current_price >= position['take_profit']) or \
                     (position['side'] == 'Sell' and current_price <= position['take_profit']):
                    self.position_manager.close_position(symbol, "Take Profit")
                    self.performance_stats['winning_trades'] += 1
                
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
            f"Производительность | "
            f"Циклы: {self.performance_stats['cycles_completed']} | "
            f"Сделки: {self.performance_stats['total_trades']} | "
            f"Винрейт: {win_rate:.1f}% | "
            f"Отклонено: {self.performance_stats['rejected_trades']} | "
            f"Активные: {self.position_manager.get_active_positions_count()} | "
            f"Баланс: {self.risk_manager.current_balance:.2f} USDT"
        )
        
        self.logger.log(performance_msg, 'info')
        
        # Детальная статистика каждые 10 циклов
        if self.performance_stats['cycles_completed'] % 10 == 0:
            detailed_stats = (
                f"Детальная статистика | "
                f"Выиграно: {self.performance_stats['winning_trades']} | "
                f"Проиграно: {self.performance_stats['losing_trades']} | "
                f"Комиссии: {self.performance_stats['total_commission']:.4f} USDT | "
                f"Просадка: {self.risk_manager.calculate_drawdown():.2%}"
            )
            self.logger.log(detailed_stats, 'info')
    
    def run(self):
        """Запуск бота"""
        self.logger.log("🚀 ПРОФЕССИОНАЛЬНЫЙ ТОРГОВЫЙ БOT ЗАПУЩЕН НА BYBIT TESTNET!", 'info', True)
        self.logger.log(f"Баланс: {self.risk_manager.current_balance} USDT", 'info', True)
        self.logger.log(f"Торговые пары: {', '.join(Config.SYMBOLS)}", 'info', True)
        
        # Настройка расписания
        schedule.every(3).minutes.do(self.run_trading_cycle)  # Каждые 3 минуты
        schedule.every(1).hours.do(self.log_performance)
        
        # Запуск первого цикла
        self.run_trading_cycle()
        
        self.logger.log("Бот работает. Нажмите Ctrl+C для остановки.", 'info')
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.logger.log("Бот остановлен пользователем", 'info', True)
                # Закрываем все позиции при остановке
                self.close_all_positions()
                break
            except Exception as e:
                self.logger.log(f"Неожиданная ошибка: {e}", 'error')
                time.sleep(60)
    
    def close_all_positions(self):
        """Закрытие всех активных позиций при остановке бота"""
        if self.position_manager.active_positions:
            self.logger.log("Закрытие всех активных позиций...", 'info')
            for symbol in list(self.position_manager.active_positions.keys()):
                self.position_manager.close_position(symbol, "Принудительное закрытие при остановке бота")

if __name__ == "__main__":
    try:
        bot = ProfessionalTradingBot()
        bot.run()
    except Exception as e:
        logger = TradingLogger()
        logger.log(f"Критическая ошибка запуска: {e}", 'error', True)