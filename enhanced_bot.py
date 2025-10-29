import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import telegram
from database import DatabaseManager

class EnhancedTradingBot:
    def __init__(self, exchange, config, symbols):
        self.exchange = exchange
        self.config = config
        self.symbols = symbols
        self.timeframe = '15m'
        self.tick_interval = 30
        self.positions = {}
        self.orders = {}
        
        # Setup logging
        self.logger = logging.getLogger('enhanced_bot')
        
        # Telegram setup
        self.telegram_enabled = bool(config.get('TELEGRAM_BOT_TOKEN') and config.get('TELEGRAM_CHAT_ID'))
        if self.telegram_enabled:
            try:
                self.telegram_bot = telegram.Bot(token=config['TELEGRAM_BOT_TOKEN'])
                self.telegram_chat_id = config['TELEGRAM_CHAT_ID']
                self.logger.info("Telegram notifications enabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize Telegram: {e}")
                self.telegram_enabled = False
        else:
            self.logger.info("Telegram notifications disabled")

    def run(self):
        self.logger.info("Starting Enhanced Trading Bot")
        while True:
            try:
                self.tick()
                time.sleep(self.tick_interval)
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(60)

    def tick(self):
        self.logger.info("=== Starting New Tick ===")
        
        # Check balance
        balance = self.check_balance()
        if not balance:
            return
            
        # Get open positions
        self.get_open_positions()
        
        # Analyze each symbol
        for symbol in self.symbols:
            try:
                data = self.get_market_data(symbol)
                if data is not None and len(data) > 0:
                    self.analyze_symbol(symbol, data, balance)
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")

    def get_market_data(self, symbol):
        try:
            # СИНХРОННЫЙ вызов - убрать await
            data = self.exchange.fetch_ohlcv(symbol, self.timeframe, since=None, limit=100)
            if data and len(data) > 0:
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
            return None
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None

    def check_balance(self):
        try:
            # СИНХРОННЫЙ вызов - убрать await
            balance = self.exchange.fetch_balance()
            usdt_balance = balance.get('total', {}).get('USDT', 0)
            self.logger.info(f"Current USDT balance: {usdt_balance}")
            return usdt_balance
        except Exception as e:
            self.logger.error(f"Error checking balance: {e}")
            return None

    def get_open_positions(self):
        try:
            # СИНХРОННЫЙ вызов - убрать await
            positions = self.exchange.fetch_positions()
            self.positions = {}
            for pos in positions:
                if float(pos.get('contracts', 0)) > 0:
                    symbol = pos['symbol']
                    self.positions[symbol] = pos
            self.logger.info(f"Open positions: {len(self.positions)}")
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")

    def analyze_symbol(self, symbol, data, balance):
        try:
            # Calculate indicators
            signals = self.calculate_indicators(data)
            
            if signals['signal'] != 'HOLD':
                self.logger.info(f"{symbol} - Signal: {signals['signal']}, Strength: {signals['strength']:.2f}")
                
                # Check if we should trade
                if self.should_trade(symbol, signals, balance):
                    self.execute_trade(symbol, signals, balance)
                    
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}")

    def calculate_indicators(self, data):
        df = data.copy()
        
        # EMA
        df['ema_short'] = df['close'].ewm(span=self.config['EMA_SHORT']).mean()
        df['ema_long'] = df['close'].ewm(span=self.config['EMA_LONG']).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config['RSI_PERIOD']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config['RSI_PERIOD']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        # Generate signals
        current_rsi = df['rsi'].iloc[-1]
        prev_ema_short = df['ema_short'].iloc[-2]
        prev_ema_long = df['ema_long'].iloc[-2]
        current_ema_short = df['ema_short'].iloc[-1]
        current_ema_long = df['ema_long'].iloc[-1]
        volume_ratio = df['volume'].iloc[-1] / df['volume_sma'].iloc[-1] if df['volume_sma'].iloc[-1] > 0 else 1
        
        signal = 'HOLD'
        strength = 0
        
        # EMA crossover
        ema_bullish = current_ema_short > current_ema_long and prev_ema_short <= prev_ema_long
        ema_bearish = current_ema_short < current_ema_long and prev_ema_short >= prev_ema_long
        
        # RSI conditions
        rsi_oversold = current_rsi < self.config['RSI_OVERSOLD']
        rsi_overbought = current_rsi > self.config['RSI_OVERBOUGHT']
        
        if ema_bullish and rsi_oversold and volume_ratio > self.config['MIN_VOLUME_RATIO']:
            signal = 'BUY'
            strength = (1 - current_rsi / self.config['RSI_OVERSOLD']) * volume_ratio
        elif ema_bearish and rsi_overbought:
            signal = 'SELL'
            strength = (current_rsi / self.config['RSI_OVERBOUGHT'] - 1) * volume_ratio
            
        return {
            'signal': signal,
            'strength': strength,
            'rsi': current_rsi,
            'volume_ratio': volume_ratio,
            'price': df['close'].iloc[-1]
        }

    def should_trade(self, symbol, signals, balance):
        # Check signal strength
        if signals['strength'] < self.config['MIN_SIGNAL_STRENGTH']:
            return False
            
        # Check max positions
        if len(self.positions) >= self.config['MAX_POSITIONS'] and symbol not in self.positions:
            return False
            
        # Check if already in position
        if symbol in self.positions:
            current_side = self.positions[symbol].get('side')
            if current_side == 'long' and signals['signal'] == 'BUY':
                return False
            if current_side == 'short' and signals['signal'] == 'SELL':
                return False
                
        return True

    def execute_trade(self, symbol, signals, balance):
        try:
            price = signals['price']
            risk_amount = balance * self.config['RISK_PER_TRADE']
            position_size = risk_amount / price
            
            # Apply position size limits
            max_size = self.config['MAX_POSITION_SIZE']
            position_size = min(position_size, max_size)
            
            if signals['signal'] == 'BUY':
                self.place_order(symbol, 'buy', position_size, price)
            elif signals['signal'] == 'SELL':
                self.place_order(symbol, 'sell', position_size, price)
                
        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {e}")

    def place_order(self, symbol, side, quantity, price):
        try:
            # Calculate order parameters
            if side == 'buy':
                order_price = price * (1 - self.config['LIMIT_ORDER_PRICE_OFFSET'])
                stop_loss = order_price * (1 - self.config['STOP_LOSS_PCT'])
                take_profit = order_price * (1 + self.config['TAKE_PROFIT_PCT'])
            else:
                order_price = price * (1 + self.config['LIMIT_ORDER_PRICE_OFFSET'])
                stop_loss = order_price * (1 + self.config['STOP_LOSS_PCT'])
                take_profit = order_price * (1 - self.config['TAKE_PROFIT_PCT'])
            
            # Place limit order
            if self.config['USE_LIMIT_ORDERS']:
                # СИНХРОННЫЙ вызов - убрать await
                order = self.exchange.create_order(
                    symbol, 
                    'limit', 
                    side, 
                    quantity, 
                    order_price
                )
            else:
                # СИНХРОННЫЙ вызов - убрать await
                order = self.exchange.create_order(
                    symbol, 
                    'market', 
                    side, 
                    quantity
                )
            
            self.logger.info(f"Placed {side} order for {quantity} {symbol} at {order_price}")
            
            # Log the trade
            self.log_trade(symbol, side, quantity, price, order['id'])
            
            # Send notification
            message = f"🎯 New Trade:\nSymbol: {symbol}\nSide: {side.upper()}\nQuantity: {quantity:.4f}\nPrice: ${price:.4f}"
            self.send_telegram_alert(message)
            
        except Exception as e:
            self.logger.error(f"Error placing order for {symbol}: {e}")

    def log_trade(self, symbol, side, quantity, price, order_id):
        if self.config['SAVE_TRADES']:
            try:
                trade_data = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'order_id': order_id
                }
                
                # Save to file
                with open(self.config['TRADE_LOG_FILE'], 'a') as f:
                    f.write(f"{trade_data}\n")
                    
            except Exception as e:
                self.logger.error(f"Error logging trade: {e}")

    def send_telegram_alert(self, message):
        if self.telegram_enabled:
            try:
                # СИНХРОННЫЙ вызов для Telegram
                self.telegram_bot.send_message(
                    chat_id=self.telegram_chat_id, 
                    text=message
                )
            except Exception as e:
                self.logger.error(f"Failed to send Telegram alert: {e}")