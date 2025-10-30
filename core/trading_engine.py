import time
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, Optional, List
import numpy as np

try:
    from enhanced_monitor import enhanced_monitor, init_enhanced_monitor
    ENHANCED_MONITOR_AVAILABLE = True
except ImportError as e:
    print(f"Enhanced monitor not available: {e}")
    ENHANCED_MONITOR_AVAILABLE = False

try:
    from risk_manager import RiskManager
    RISK_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Risk manager not available: {e}")
    RISK_MANAGER_AVAILABLE = False

class TradingEngine:
    def __init__(self, api, strategy, config):
        self.api = api
        self.strategy = strategy
        self.config = config
        self.is_running = False
        self.active_positions = {}
        self.pair_signals = {}
        self.cycle_count = 0
        self.setup_logging()
        
        # Инициализация улучшенного мониторинга если доступен
        if ENHANCED_MONITOR_AVAILABLE:
            init_enhanced_monitor(config)
        else:
            self.logger.warning("Enhanced monitor not available - using basic logging")
            
        # Инициализация риск-менеджера
        if RISK_MANAGER_AVAILABLE:
            self.risk_manager = RiskManager(config, api)
        else:
            self.risk_manager = None
            self.logger.warning("Risk manager not available - using fixed position sizes")
        
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
        """Инициализация торговли для всех пар"""
        try:
            # Проверка подключения к API
            server_time = self.api.get_server_time()
            if not server_time:
                self.logger.error("Failed to connect to Bybit API - cannot get server time")
                return False
                
            self.logger.info(f"Connected to Bybit API. Server time: {server_time['result']['timeSecond']}")
            
            # Проверка баланса
            balance = self.api.get_account_balance(self.config.ACCOUNT_TYPE)
            if not balance:
                self.logger.error("Failed to get account balance")
                return False
                
            # Логирование информации о балансе
            if 'result' in balance and 'list' in balance['result']:
                account_info = balance['result']['list'][0]
                total_equity = account_info.get('totalEquity', '0')
                self.logger.info(f"Account type: {account_info.get('accountType')}")
                self.logger.info(f"Total equity: {total_equity}")
                
                # Поиск USDT баланса
                coins = account_info.get('coin', [])
                for coin in coins:
                    if coin.get('coin') == 'USDT':
                        available = coin.get('availableToWithdraw', '0')
                        wallet = coin.get('walletBalance', '0')
                        self.logger.info(f"USDT Wallet: {wallet}, Available: {available}")
                        break
            
            # Инициализация для каждой пары
            self.logger.info(f"Initializing trading for pairs: {', '.join(self.config.TRADING_PAIRS)}")
            
            for pair in self.config.TRADING_PAIRS:
                pair_settings = self.config.get_pair_settings(pair)
                self.logger.info(f"Pair {pair}: amount={pair_settings['trade_amount']}, leverage={pair_settings['leverage']}")
                # Инициализация отслеживания позиций
                self.active_positions[pair] = {
                    'size': 0,
                    'side': None,
                    'entry_price': 0
                }
            
            self.logger.info("Multi-pair trading initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    def get_market_data(self, pair: str) -> Optional[pd.DataFrame]:
        """Получение рыночных данных для конкретной пары"""
        try:
            kline_data = self.api.get_kline(
                category=self.config.CATEGORY,
                symbol=pair,
                interval='5',  # 5 минут
                limit=100
            )
            
            if not kline_data:
                return None
                
            if 'result' in kline_data and 'list' in kline_data['result']:
                df = pd.DataFrame(kline_data['result']['list'])
                
                if len(df.columns) >= 7:
                    # Переименование колонок
                    df = df.rename(columns={
                        0: 'timestamp',
                        1: 'open',
                        2: 'high', 
                        3: 'low',
                        4: 'close',
                        5: 'volume',
                        6: 'turnover'
                    })
                    
                    # Конвертация типов
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                    # Сортировка по времени
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    
                    return df
                else:
                    self.logger.error(f"Unexpected kline data structure for {pair}: {df.columns}")
                    return None
            else:
                self.logger.error(f"Unexpected kline data format for {pair}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting market data for {pair}: {e}")
            return None

    def analyze_portfolio_correlation(self, all_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Анализ корреляции между активами"""
        correlations = {}
        
        try:
            # Создаем DataFrame с ценами закрытия всех пар
            close_prices = {}
            for pair, df in all_data.items():
                if df is not None and not df.empty:
                    close_prices[pair] = df['close']
            
            if len(close_prices) > 1:
                correlation_df = pd.DataFrame(close_prices)
                correlation_matrix = correlation_df.corr()
                
                # Средняя корреляция для каждого актива
                for pair in self.config.TRADING_PAIRS:
                    if pair in correlation_matrix.columns:
                        # Исключаем корреляцию с самим собой
                        other_pairs = [p for p in correlation_matrix.columns if p != pair]
                        if other_pairs:
                            avg_correlation = correlation_matrix.loc[pair, other_pairs].mean()
                            correlations[pair] = avg_correlation
                            
            self.logger.debug(f"Portfolio correlations: {correlations}")
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio correlation: {e}")
            
        return correlations

    def can_open_new_position(self, pair: str, signal: str, correlations: Dict[str, float]) -> bool:
        """Проверка возможности открытия новой позиции"""
        # Подсчет активных позиций
        active_count = sum(1 for pos in self.active_positions.values() if pos['size'] > 0)
        
        if active_count >= self.config.MAX_CONCURRENT_TRADES:
            self.logger.info(f"Cannot open {pair} position: maximum concurrent trades reached ({active_count})")
            return False
            
        # Проверка корреляции (если включена диверсификация)
        if self.config.ENABLE_PORTFOLIO_DIVERSIFICATION and pair in correlations:
            if correlations[pair] > self.config.CORRELATION_THRESHOLD:
                self.logger.info(f"Cannot open {pair} position: high correlation with portfolio ({correlations[pair]:.3f})")
                return False
                
        return True

    def execute_trading_cycle(self):
        """Выполнение торгового цикла для всех пар"""
        try:
            all_data = {}
            current_prices = {}
            
            # Сбор данных для всех пар
            for pair in self.config.TRADING_PAIRS:
                df = self.get_market_data(pair)
                if df is not None and not df.empty:
                    all_data[pair] = df
                    # Сохранение текущей цены
                    current_prices[pair] = df['close'].iloc[-1]
                    self.logger.debug(f"{pair} price: {current_prices[pair]:.2f}")

            # Анализ корреляции портфеля
            correlations = self.analyze_portfolio_correlation(all_data)
            
            # Обработка каждой пары
            for pair, df in all_data.items():
                if len(df) < 100:
                    self.logger.debug(f"Not enough data for {pair}")
                    continue
                    
                # Расчет индикаторов
                df = self.strategy.calculate_indicators(df)
                
                # Генерация сигнала
                signal = self.strategy.generate_signal(df)
                self.pair_signals[pair] = signal
                
                # Логирование сигналов
                latest = df.iloc[-1]
                self.logger.info(f"{pair} signal: {signal['signal']} - {signal['reason']}")
                
                # Детальное логирование индикаторов
                indicators_info = []
                indicator_values = {}
                
                if 'rsi' in latest and not pd.isna(latest['rsi']):
                    rsi_val = latest['rsi']
                    indicators_info.append(f"RSI: {rsi_val:.2f}")
                    indicator_values['rsi'] = rsi_val
                    
                if 'macd' in latest and not pd.isna(latest['macd']):
                    macd_val = latest['macd']
                    indicators_info.append(f"MACD: {macd_val:.2f}")
                    indicator_values['macd'] = macd_val
                    
                if 'ema_20' in latest and not pd.isna(latest['ema_20']):
                    ema_20_val = latest['ema_20']
                    indicators_info.append(f"EMA20: {ema_20_val:.2f}")
                    indicator_values['ema_20'] = ema_20_val
                    
                if 'ema_50' in latest and not pd.isna(latest['ema_50']):
                    ema_50_val = latest['ema_50']
                    indicators_info.append(f"EMA50: {ema_50_val:.2f}")
                    indicator_values['ema_50'] = ema_50_val
                
                if indicators_info:
                    self.logger.debug(f"{pair} indicators: {', '.join(indicators_info)}")
                
                # Логирование в улучшенный монитор
                if ENHANCED_MONITOR_AVAILABLE and enhanced_monitor:
                    cycle_data = {
                        'cycle': self.cycle_count,
                        'pair': pair,
                        'signal': signal['signal'],
                        'reason': signal['reason'],
                        'price': current_prices[pair],
                        'indicators': indicator_values,
                        'correlation': correlations.get(pair, 0)
                    }
                    enhanced_monitor.log_trading_cycle(cycle_data)
                
                # Исполнение сигнала
                if signal['signal'] == 'BUY':
                    if self.can_open_new_position(pair, 'BUY', correlations):
                        self.execute_buy(pair)
                elif signal['signal'] == 'SELL':
                    self.execute_sell(pair)
                    
        except Exception as e:
            self.logger.error(f"Trading cycle error: {e}")

    def execute_buy(self, pair: str):
        """Исполнение buy сигнала для конкретной пары"""
        try:
            # Проверка существующей позиции
            positions = self.api.get_positions(
                category=self.config.CATEGORY,
                symbol=pair
            )
            
            has_long_position = False
            if positions and 'result' in positions and 'list' in positions['result']:
                for position in positions['result']['list']:
                    if (position['symbol'] == pair and 
                        float(position.get('size', 0)) > 0):
                        has_long_position = True
                        self.active_positions[pair] = {
                            'size': float(position.get('size', 0)),
                            'side': 'Buy',
                            'entry_price': float(position.get('avgPrice', 0))
                        }
                        break

            if has_long_position:
                self.logger.info(f"Long position already exists for {pair}")
                return

            # Получаем текущую цену
            current_price_data = self.get_market_data(pair)
            if current_price_data is None or current_price_data.empty:
                self.logger.error(f"Cannot get current price for {pair}")
                return
                
            current_price = current_price_data['close'].iloc[-1]
            
            # Расчет размера позиции с защитой от ошибок
            trade_amount = None
            trade_info = {}
            
            try:
                if self.risk_manager:
                    # Используем риск-менеджер для расчета размера
                    trade_amount = self.risk_manager.calculate_position_size(pair, current_price)
                    
                    # Получаем информацию о стоимости
                    trade_info = self.risk_manager.get_trade_value_info(pair, trade_amount, current_price)
                    
                    # Проверка на пропуск сделки из-за риска
                    volatility = self.calculate_volatility(current_price_data)
                    if self.risk_manager.should_skip_trade(pair, 'BUY', volatility):
                        self.logger.info(f"Skipping BUY for {pair} due to risk management")
                        return
            except Exception as e:
                self.logger.warning(f"Risk manager failed for {pair}: {e}. Using fixed amount.")
            
            # Если risk_manager не сработал, используем фиксированный размер
            if trade_amount is None:
                pair_settings = self.config.get_pair_settings(pair)
                trade_amount = pair_settings['trade_amount']
                trade_info = {
                    'position_value_usdt': trade_amount * current_price,
                    'leverage': pair_settings['leverage']
                }
            
            # Детальное логирование
            self.logger.info(f"TRADE DETAILS for {pair}:")
            self.logger.info(f"  Amount: {trade_amount:.6f}")
            self.logger.info(f"  Price: ${current_price:.2f}")
            self.logger.info(f"  Position Value: ${trade_info['position_value_usdt']:.2f} USDT")
            self.logger.info(f"  Leverage: {trade_info['leverage']}x")
            
            # Размещение ордера
            self.logger.info(f"Executing BUY order for {trade_amount:.6f} {pair}")
            result = self.api.place_order(
                category=self.config.CATEGORY,
                symbol=pair,
                side='Buy',
                order_type='Market',
                qty=trade_amount
            )
            
            if result:
                self.logger.info(f"Buy order for {pair} executed successfully")
                if 'result' in result:
                    order_id = result['result'].get('orderId')
                    self.logger.info(f"Order ID: {order_id}")
                    # Обновление информации о позиции
                    self.active_positions[pair] = {
                        'size': trade_amount,
                        'side': 'Buy',
                        'entry_price': current_price,
                        'position_value': trade_info['position_value_usdt']
                    }
            else:
                self.logger.error(f"Buy order for {pair} failed")
                
        except Exception as e:
            self.logger.error(f"Error executing buy for {pair}: {e}")

    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Расчет волатильности на основе исторических данных"""
        if len(df) < period:
            return 0.0
            
        returns = df['close'].pct_change().dropna()
        volatility = returns.rolling(window=period).std().iloc[-1] * 100  # в процентах
        return volatility

    def execute_sell(self, pair: str):
        """Исполнение sell сигнала для конкретной пары"""
        try:
            # Проверка существующей позиции
            positions = self.api.get_positions(
                category=self.config.CATEGORY,
                symbol=pair
            )
            
            position_size = 0
            if positions and 'result' in positions and 'list' in positions['result']:
                for position in positions['result']['list']:
                    if position['symbol'] == pair:
                        position_size = float(position.get('size', 0))
                        break

            if position_size > 0:
                # Получение настроек пары
                pair_settings = self.config.get_pair_settings(pair)
                
                # Закрытие длинной позиции
                self.logger.info(f"Executing SELL order for {pair_settings['trade_amount']} {pair}")
                result = self.api.place_order(
                    category=self.config.CATEGORY,
                    symbol=pair,
                    side='Sell',
                    order_type='Market',
                    qty=min(pair_settings['trade_amount'], position_size)
                )
                
                if result:
                    self.logger.info(f"Sell order for {pair} executed successfully")
                    if 'result' in result:
                        self.logger.info(f"Order ID: {result['result'].get('orderId')}")
                    # Сброс информации о позиции
                    self.active_positions[pair] = {'size': 0, 'side': None, 'entry_price': 0}
                else:
                    self.logger.error(f"Sell order for {pair} failed")
            else:
                self.logger.info(f"No long position to close for {pair}")
                self.active_positions[pair] = {'size': 0, 'side': None, 'entry_price': 0}
                
        except Exception as e:
            self.logger.error(f"Error executing sell for {pair}: {e}")

    def get_portfolio_summary(self):
        """Получение сводки по портфелю"""
        active_trades = sum(1 for pos in self.active_positions.values() if pos['size'] > 0)
        
        summary = {
            'total_pairs': len(self.config.TRADING_PAIRS),
            'active_trades': active_trades,
            'max_concurrent_trades': self.config.MAX_CONCURRENT_TRADES,
            'active_positions': {k: v for k, v in self.active_positions.items() if v['size'] > 0},
            'latest_signals': self.pair_signals
        }
        
        return summary

    def run(self):
        """Запуск торгового движка"""
        self.logger.info("Starting multi-pair trading engine...")
        
        if not self.initialize_trading():
            self.logger.error("Failed to initialize trading")
            return
            
        self.is_running = True
        
        while self.is_running:
            try:
                self.cycle_count += 1
                self.logger.info(f"=== Trading cycle {self.cycle_count} ===")
                
                self.execute_trading_cycle()
                
                # Логирование сводки портфеля
                portfolio_summary = self.get_portfolio_summary()
                
                # Вывод дашборда в консоль
                if ENHANCED_MONITOR_AVAILABLE and enhanced_monitor:
                    enhanced_monitor.print_real_time_dashboard(self.pair_signals, portfolio_summary)
                    enhanced_monitor.log_portfolio_status(portfolio_summary)
                else:
                    # Базовый вывод если улучшенный монитор недоступен
                    self.logger.info(f"Portfolio: {portfolio_summary['active_trades']}/{portfolio_summary['max_concurrent_trades']} active trades")
                    self.logger.info("Active positions:")
                    for pair, position in portfolio_summary['active_positions'].items():
                        self.logger.info(f"  {pair}: {position['size']} units")
                
                # Пауза между циклами
                self.logger.info(f"Waiting 60 seconds until next cycle...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                self.logger.info("Trading stopped by user")
                # Сохранение истории перед выходом
                if ENHANCED_MONITOR_AVAILABLE and enhanced_monitor:
                    enhanced_monitor.save_history()
                    report = enhanced_monitor.generate_detailed_report()
                    self.logger.info(f"Final report: {report}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(60)