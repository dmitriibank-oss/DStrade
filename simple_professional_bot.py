import time
import schedule
from datetime import datetime
from config.config import Config
from src.bybit_client import BybitClient
from src.symbol_info import SymbolInfo
from src.logger import TradingLogger

class SimpleProfessionalBot:
    def __init__(self):
        self.client = BybitClient()
        self.symbol_info = SymbolInfo()
        self.logger = TradingLogger()
        
        # Проверка подключения
        if not self.client.test_connection():
            raise Exception("Не удалось подключиться к Bybit API")
        
        # Инициализация баланса
        self.balance = self.client.get_account_balance()
        self.initial_balance = self.balance
        
        self.performance_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'cycles_completed': 0,
            'total_volume': 0,
            'rejected_trades': 0
        }
        
        # Используем только символы с подходящими условиями
        self.test_symbols = ['SOLUSDT', 'XRPUSDT']
        
        self.logger.log(f"Упрощенный профессиональный бот инициализирован с балансом: {self.balance} USDT", 'info', True)
    
    def simple_analysis(self, symbol):
        """Простой анализ на основе цены"""
        try:
            # Получаем текущую цену
            current_price = self.client.get_current_price(symbol)
            if not current_price:
                return 'HOLD'
            
            # Получаем исторические данные
            df = self.client.get_klines(symbol, limit=50)
            if df is None or len(df) < 20:
                return 'HOLD'
            
            # Простые расчеты
            current_close = df['close'].iloc[-1]
            prev_close = df['close'].iloc[-2]
            sma_10 = df['close'].tail(10).mean()
            sma_20 = df['close'].tail(20).mean()
            
            # Простая логика
            signals = []
            
            # Тренд
            if current_close > sma_20:
                signals.append('UPTREND')
            else:
                signals.append('DOWNTREND')
            
            # Моментум
            if current_close > prev_close:
                signals.append('UP_MOMENTUM')
            else:
                signals.append('DOWN_MOMENTUM')
            
            # Простая стратегия: покупать при восходящем тренде и моментуме
            if 'UPTREND' in signals and 'UP_MOMENTUM' in signals:
                return 'BUY'
            elif 'DOWNTREND' in signals and 'DOWN_MOMENTUM' in signals:
                return 'SELL'
            else:
                return 'HOLD'
                
        except Exception as e:
            self.logger.log(f"Ошибка анализа {symbol}: {e}", 'error')
            return 'HOLD'
    
    def calculate_position_size(self, symbol, current_price):
        """Расчет размера позиции с учетом всех ограничений Bybit"""
        try:
            # Базовый размер позиции в USDT (увеличили для тестирования)
            base_position_usdt = 10.0  # 10 USDT для уверенного прохождения минимальных лимитов
            
            # Рассчитываем правильное количество с учетом всех ограничений
            quantity = self.symbol_info.calculate_proper_quantity(symbol, base_position_usdt, current_price)
            
            # Финальная проверка
            is_valid, validation_msg = self.symbol_info.validate_order_quantity(symbol, quantity, current_price)
            
            if not is_valid:
                self.logger.log(f"Невалидная позиция для {symbol}: {validation_msg}", 'warning')
                return 0
            
            order_value = quantity * current_price
            self.logger.log(f"Рассчитана позиция для {symbol}: {quantity} (стоимость: {order_value:.2f} USDT)", 'info')
            
            return quantity
            
        except Exception as e:
            self.logger.log(f"Ошибка расчета позиции для {symbol}: {e}", 'error')
            return 0
    
    def run_trading_cycle(self):
        """Упрощенный торговый цикл"""
        try:
            self.performance_stats['cycles_completed'] += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logger.log(f"Цикл #{self.performance_stats['cycles_completed']} в {current_time}", 'info')
            
            # Обновляем баланс
            self.balance = self.client.get_account_balance()
            
            # Анализируем каждый символ
            for symbol in self.test_symbols:
                signal = self.simple_analysis(symbol)
                current_price = self.client.get_current_price(symbol)
                
                if signal in ['BUY', 'SELL'] and current_price:
                    self.logger.log(f"Сигнал для {symbol}: {signal} по цене {current_price}", 'info')
                    
                    # Рассчитываем размер позиции
                    position_size = self.calculate_position_size(symbol, current_price)
                    
                    if position_size > 0:
                        # Размещаем ордер
                        order = self.client.place_order(symbol, signal, position_size)
                        if order:
                            self.performance_stats['total_trades'] += 1
                            self.performance_stats['successful_trades'] += 1
                            order_value = position_size * current_price
                            self.performance_stats['total_volume'] += order_value
                            self.logger.log(f"Тестовая сделка выполнена: {signal} {position_size} {symbol} (стоимость: {order_value:.2f} USDT)", 'info', True)
                        else:
                            self.performance_stats['total_trades'] += 1
                            self.performance_stats['failed_trades'] += 1
                            self.logger.log(f"Тестовая сделка не удалась: {signal} {position_size} {symbol}", 'warning')
                    else:
                        self.performance_stats['rejected_trades'] += 1
                        self.logger.log(f"Сделка отклонена: не удалось рассчитать валидный размер позиции для {symbol}", 'info')
                    
                    # Пауза между ордерами
                    time.sleep(2)
                else:
                    self.logger.log(f"Нет сигнала для {symbol} или не удалось получить цену", 'info')
            
            # Логируем производительность
            self.log_performance()
            
        except Exception as e:
            self.logger.log(f"Ошибка в торговом цикле: {e}", 'error')
    
    def log_performance(self):
        """Логирование производительности"""
        success_rate = 0
        if self.performance_stats['total_trades'] > 0:
            success_rate = (self.performance_stats['successful_trades'] / self.performance_stats['total_trades']) * 100
        
        avg_trade_size = 0
        if self.performance_stats['successful_trades'] > 0:
            avg_trade_size = self.performance_stats['total_volume'] / self.performance_stats['successful_trades']
        
        performance_msg = (
            f"Производительность | "
            f"Циклы: {self.performance_stats['cycles_completed']} | "
            f"Сделки: {self.performance_stats['total_trades']} | "
            f"Успешные: {self.performance_stats['successful_trades']} | "
            f"Неудачные: {self.performance_stats['failed_trades']} | "
            f"Отклонено: {self.performance_stats['rejected_trades']} | "
            f"Успех: {success_rate:.1f}% | "
            f"Объем: {self.performance_stats['total_volume']:.2f} USDT | "
            f"Баланс: {self.balance:.2f} USDT"
        )
        self.logger.log(performance_msg, 'info')
    
    def run(self):
        """Запуск бота"""
        self.logger.log("🚀 УПРОЩЕННЫЙ ПРОФЕССИОНАЛЬНЫЙ БОТ ЗАПУЩЕН!", 'info', True)
        self.logger.log(f"Тестовые символы: {', '.join(self.test_symbols)}", 'info')
        self.logger.log(f"Начальный баланс: {self.balance} USDT", 'info')
        
        # Настройка расписания
        schedule.every(5).minutes.do(self.run_trading_cycle)  # Каждые 5 минут
        
        # Первый запуск
        self.run_trading_cycle()
        
        self.logger.log("Бот работает. Нажмите Ctrl+C для остановки.", 'info')
        
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
        bot = SimpleProfessionalBot()
        bot.run()
    except Exception as e:
        logger = TradingLogger()
        logger.log(f"Критическая ошибка запуска: {e}", 'error', True)