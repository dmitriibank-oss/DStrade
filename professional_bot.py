import time
import schedule
from datetime import datetime
from config.config import Config
from src.bybit_client import BybitClient
from src.trading_strategy import TradingStrategy
from src.position_manager import PositionManager
from src.risk_manager import RiskManager
from src.symbol_info import SymbolInfo
from src.logger import TradingLogger

class ProfessionalTradingBot:
    def __init__(self):
        self.logger = TradingLogger()
        self.client = BybitClient()
        self.strategy = TradingStrategy()
        self.symbol_info = SymbolInfo()
        
        # Получаем баланс
        self.initial_balance = self.client.get_account_balance()
        self.risk_manager = RiskManager(self.initial_balance)
        self.position_manager = PositionManager(self.client)
        
        self.cycle_count = 0
        self.total_trades = 0
        
        self.logger.log(f"Бот инициализирован с балансом: {self.initial_balance} USDT", 'info')
    
    def run_trading_cycle(self):
        """Консервативный цикл торговли"""
        self.cycle_count += 1
        self.logger.log(f"Цикл #{self.cycle_count} в {datetime.now()}", 'info')
        
        try:
            # Получаем баланс
            balance = self.client.get_account_balance()
            self.risk_manager.update_balance(balance)
            
            # Проверяем риски
            if not self.risk_manager.can_trade():
                self.logger.log("Торговля приостановлена по рискам", 'warning')
                return
            
            active_positions = self.position_manager.get_active_positions_count()
            
            # Обрабатываем символы только если есть свободные слоты
            if active_positions < Config.MAX_POSITIONS:
                for symbol in Config.SYMBOLS:
                    if symbol not in self.position_manager.active_positions:
                        self.process_symbol(symbol, balance)
            
            # Логируем статистику
            self.log_statistics(balance, active_positions)
            
        except Exception as e:
            self.logger.log(f"Ошибка в цикле торговли: {e}", 'error')
    
    def process_symbol(self, symbol, balance):
        """Обработка символа"""
        try:
            # Получаем данные
            df = self.client.get_klines(symbol, '15', 100)
            if df is None or len(df) < 50:
                return
            
            # Анализируем
            signal, details, signal_strength = self.strategy.analyze_symbol(symbol, df)
            
            if signal != 'HOLD':
                current_price = self.client.get_current_price(symbol)
                if current_price:
                    self.execute_trade(symbol, signal, details, current_price, balance, signal_strength)
                    
        except Exception as e:
            self.logger.log(f"Ошибка обработки {symbol}: {e}", 'error')
    
    def execute_trade(self, symbol, signal, details, current_price, balance, signal_strength):
        """Исполнение сделки"""
        try:
            # Расчет уровней
            if signal == 'BUY':
                stop_loss = current_price * (1 - Config.STOP_LOSS_PCT)
                take_profit = current_price * (1 + Config.TAKE_PROFIT_PCT)
            else:
                stop_loss = current_price * (1 + Config.STOP_LOSS_PCT)
                take_profit = current_price * (1 - Config.TAKE_PROFIT_PCT)
            
            # Расчет размера позиции
            position_size = self.strategy.calculate_position_size(
                balance, current_price, stop_loss, signal_strength
            )
            
            if position_size <= 0:
                return
            
            # Расчет правильного количества
            quantity = self.symbol_info.calculate_proper_quantity(
                symbol, position_size * current_price, current_price
            )
            
            # Открываем позицию
            if self.position_manager.open_position(symbol, signal, quantity, current_price, stop_loss, take_profit):
                self.total_trades += 1
                self.risk_manager.record_trade(symbol, signal, current_price, quantity, stop_loss, take_profit)
                self.logger.log(
                    f"🎯 СДЕЛКА: {signal} {quantity:.4f} {symbol} | "
                    f"Цена: {current_price:.4f} | Сила: {signal_strength:.1f}",
                    'info', 
                    True
                )
                
        except Exception as e:
            self.logger.log(f"Ошибка исполнения сделки: {e}", 'error')
    
    def log_statistics(self, balance, active_positions):
        """Логирование статистики"""
        self.logger.log(
            f"СТАТИСТИКА | Циклы: {self.cycle_count} | "
            f"Сделки: {self.total_trades} | Активные: {active_positions} | "
            f"Баланс: {balance:.2f} USDT",
            'info'
        )

def main():
    try:
        bot = ProfessionalTradingBot()
        
        # Тест подключения
        if not bot.client.test_connection():
            bot.logger.log("Ошибка подключения к API", 'error', True)
            return
        
        bot.logger.log("🚀 ТОРГОВЫЙ БОТ ЗАПУЩЕН", 'info', True)
        bot.logger.log(f"Баланс: {bot.initial_balance} USDT", 'info')
        bot.logger.log(f"Символы: {', '.join(Config.SYMBOLS)}", 'info')
        
        # Запускаем каждые 10 минут
        schedule.every(10).minutes.do(bot.run_trading_cycle)
        
        # Первый запуск
        bot.run_trading_cycle()
        
        bot.logger.log("Бот работает. Ctrl+C для остановки.", 'info')
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except KeyboardInterrupt:
                bot.logger.log("Бот остановлен", 'info', True)
                break
            except Exception as e:
                bot.logger.log(f"Ошибка: {e}", 'error')
                time.sleep(60)
                
    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()