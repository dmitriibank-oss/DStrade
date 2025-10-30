import time
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, Optional
import numpy as np

class SimpleTradingEngine:
    """Упрощенная версия торгового движка без risk_manager"""
    
    def __init__(self, api, strategy, config):
        self.api = api
        self.strategy = strategy
        self.config = config
        self.is_running = False
        self.active_positions = {}
        self.pair_signals = {}
        self.cycle_count = 0
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def initialize_trading(self):
        """Инициализация торговли"""
        try:
            server_time = self.api.get_server_time()
            if not server_time:
                self.logger.error("Failed to connect to Bybit API")
                return False
                
            self.logger.info(f"Connected to Bybit API. Server time: {server_time['result']['timeSecond']}")
            
            # Инициализация для каждой пары
            for pair in self.config.TRADING_PAIRS:
                pair_settings = self.config.get_pair_settings(pair)
                self.logger.info(f"Pair {pair}: amount={pair_settings['trade_amount']}, leverage={pair_settings['leverage']}")
                self.active_positions[pair] = {
                    'size': 0,
                    'side': None,
                    'entry_price': 0
                }
            
            self.logger.info("Simple trading initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    def get_market_data(self, pair: str) -> Optional[pd.DataFrame]:
        """Получение рыночных данных"""
        try:
            kline_data = self.api.get_kline(
                category=self.config.CATEGORY,
                symbol=pair,
                interval='5',
                limit=100
            )
            
            if not kline_data or 'result' not in kline_data or 'list' not in kline_data['result']:
                return None
                
            df = pd.DataFrame(kline_data['result']['list'])
            
            if len(df.columns) >= 7:
                df = df.rename(columns={
                    0: 'timestamp', 1: 'open', 2: 'high', 3: 'low', 
                    4: 'close', 5: 'volume', 6: 'turnover'
                })
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                df = df.sort_values('timestamp').reset_index(drop=True)
                return df
                
        except Exception as e:
            self.logger.error(f"Error getting market data for {pair}: {e}")
        return None

    def execute_trading_cycle(self):
        """Выполнение торгового цикла"""
        try:
            for pair in self.config.TRADING_PAIRS:
                df = self.get_market_data(pair)
                if df is None or len(df) < 100:
                    continue
                    
                # Расчет индикаторов
                df = self.strategy.calculate_indicators(df)
                
                # Генерация сигнала
                signal = self.strategy.generate_signal(df)
                self.pair_signals[pair] = signal
                
                self.logger.info(f"{pair} signal: {signal['signal']} - {signal['reason']}")
                
                # Исполнение сигнала с фиксированным размером
                if signal['signal'] == 'BUY':
                    self.execute_simple_buy(pair)
                elif signal['signal'] == 'SELL':
                    self.execute_simple_sell(pair)
                    
        except Exception as e:
            self.logger.error(f"Trading cycle error: {e}")

    def execute_simple_buy(self, pair: str):
        """Упрощенное исполнение buy сигнала"""
        try:
            # Проверка существующей позиции с указанием символа
            positions = self.api.get_positions(
                category=self.config.CATEGORY,
                symbol=pair  # Явно указываем символ
            )
            
            has_long_position = False
            if positions and 'result' in positions and 'list' in positions['result']:
                for position in positions['result']['list']:
                    if position['symbol'] == pair and float(position.get('size', 0)) > 0:
                        has_long_position = True
                        # Обновляем информацию о позиции
                        self.active_positions[pair] = {
                            'size': float(position.get('size', 0)),
                            'side': position.get('side', 'Unknown'),
                            'entry_price': float(position.get('avgPrice', 0)),
                            'unrealised_pnl': float(position.get('unrealisedPnl', 0))
                        }
                        self.logger.info(f"Found existing {pair} position: {position['size']} units")
                        break

            if has_long_position:
                self.logger.info(f"Long position already exists for {pair}")
                return

            # Используем фиксированный размер из настроек
            pair_settings = self.config.get_pair_settings(pair)
            trade_amount = pair_settings['trade_amount']
            
            # Получаем текущую цену для логирования
            current_price_data = self.get_market_data(pair)
            current_price = current_price_data['close'].iloc[-1] if current_price_data is not None else 0
            
            position_value = trade_amount * current_price
            
            self.logger.info(f"Executing BUY order for {trade_amount} {pair} (~${position_value:.2f})")
            
            # Размещение ордера
            result = self.api.place_order(
                category=self.config.CATEGORY,
                symbol=pair,
                side='Buy',
                order_type='Market',
                qty=trade_amount
            )
            
            if result:
                self.logger.info(f"✅ Buy order for {pair} executed successfully!")
                if 'result' in result:
                    order_id = result['result'].get('orderId')
                    self.logger.info(f"Order ID: {order_id}")
                    # Обновление информации о позиции
                    self.active_positions[pair] = {
                        'size': trade_amount,
                        'side': 'Buy',
                        'entry_price': current_price,
                        'position_value': position_value
                    }
            else:
                self.logger.error(f"❌ Buy order for {pair} failed")
                
        except Exception as e:
            self.logger.error(f"Error executing buy for {pair}: {e}")

    def execute_simple_sell(self, pair: str):
        """Упрощенное исполнение sell сигнала"""
        try:
            # Проверка существующей позиции с указанием символа
            positions = self.api.get_positions(
                category=self.config.CATEGORY,
                symbol=pair  # Явно указываем символ
            )
            
            position_size = 0
            if positions and 'result' in positions and 'list' in positions['result']:
                for position in positions['result']['list']:
                    if position['symbol'] == pair:
                        position_size = float(position.get('size', 0))
                        break

            if position_size > 0:
                pair_settings = self.config.get_pair_settings(pair)
                trade_amount = min(pair_settings['trade_amount'], position_size)
                
                self.logger.info(f"Executing SELL order for {trade_amount} {pair}")
                
                result = self.api.place_order(
                    category=self.config.CATEGORY,
                    symbol=pair,
                    side='Sell',
                    order_type='Market',
                    qty=trade_amount
                )
                
                if result:
                    self.logger.info(f"✅ Sell order for {pair} executed successfully!")
                    if 'result' in result:
                        self.logger.info(f"Order ID: {result['result'].get('orderId')}")
                    # Сбрасываем информацию о позиции
                    self.active_positions[pair] = {'size': 0, 'side': None, 'entry_price': 0}
                else:
                    self.logger.error(f"❌ Sell order for {pair} failed")
            else:
                self.logger.info(f"No long position to close for {pair}")
                self.active_positions[pair] = {'size': 0, 'side': None, 'entry_price': 0}
                    
        except Exception as e:
            self.logger.error(f"Error executing sell for {pair}: {e}")

    def print_trading_dashboard(self):
        """Вывод дашборда торговли"""
        print("\n" + "="*60)
        print(f"TRADING DASHBOARD - Cycle {self.cycle_count}")
        print("="*60)
        
        # Активные позиции
        active_count = sum(1 for pos in self.active_positions.values() if pos['size'] > 0)
        print(f"📊 Active Positions: {active_count}/{self.config.MAX_CONCURRENT_TRADES}")
        
        # Сигналы
        print(f"📈 Current Signals:")
        for pair, signal in self.pair_signals.items():
            icon = "🟢" if signal['signal'] == 'BUY' else "🔴" if signal['signal'] == 'SELL' else "⚪"
            print(f"   {icon} {pair}: {signal['signal']} - {signal['reason'][:40]}...")
        
        print("="*60)

    # Добавьте вызов в метод run после execute_trading_cycle
    def run(self):
        """Запуск упрощенного торгового движка"""
        self.logger.info("Starting simple trading engine...")
        
        if not self.initialize_trading():
            return
            
        self.is_running = True
        
        while self.is_running:
            try:
                self.cycle_count += 1
                self.logger.info(f"=== Trading cycle {self.cycle_count} ===")
                
                self.execute_trading_cycle()
                
                # Вывод дашборда
                self.print_trading_dashboard()
                
                # Пауза между циклами
                self.logger.info(f"Waiting 60 seconds until next cycle...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                self.logger.info("Trading stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                time.sleep(60)