import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from src.risk_management.advanced_risk_manager import AdvancedRiskManager
from src.strategies.enhanced_ml_strategy import EnhancedMLStrategy, EnhancedSignal

class EnhancedTradingBot:
    def __init__(self, exchange, config: Dict, db_manager=None):
        self.exchange = exchange
        self.config = config
        self.db_manager = db_manager
        
        # Initialize components
        self.risk_manager = AdvancedRiskManager(config)
        self.strategy = EnhancedMLStrategy(config)
        
        # Trading state
        self.active_positions = {}
        self.pending_orders = {}
        self.is_running = False
        
        # Performance tracking
        self.performance_history = []
        
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/enhanced_bot.log'),
                logging.StreamHandler()
            ]
        )
    
    async def run(self):
        """Main trading loop"""
        self.is_running = True
        self.logger.info("Starting Enhanced Trading Bot")
        
        try:
            while self.is_running:
                try:
                    # Check risk limits
                    if self.risk_manager.should_stop_trading():
                        self.logger.error("Trading stopped due to risk limits")
                        break
                    
                    # Process each symbol
                    for symbol in self.config.get('symbols', []):
                        await self.process_symbol(symbol)
                    
                    # Update performance metrics
                    self._update_performance_metrics()
                    
                    # Sleep between iterations
                    await asyncio.sleep(self.config.get('tick_interval', 60))
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    await asyncio.sleep(10)
                    
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        finally:
            await self.cleanup()
    
    async def process_symbol(self, symbol: str):
        """Process trading for a specific symbol"""
        try:
            # Get market data
            market_data = await self.get_market_data(symbol)
            if not market_data:
                return
            
            # Generate trading signal
            signal = self.strategy.generate_signal(symbol, market_data)
            
            # Check if we should enter a trade
            if signal.action != "HOLD" and signal.confidence > self.strategy.min_confidence:
                if symbol not in self.active_positions:
                    await self.enter_trade(signal, market_data)
                else:
                    self.logger.debug(f"Already in position for {symbol}, skipping new entry")
            
            # Monitor existing position
            if symbol in self.active_positions:
                await self.monitor_position(symbol, market_data)
                
        except Exception as e:
            self.logger.error(f"Error processing symbol {symbol}: {e}")
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get comprehensive market data for a symbol"""
        try:
            # Get OHLCV data
            timeframe = self.config.get('timeframe', '1m')
            limit = self.config.get('data_limit', 100)
            
            candles = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not candles:
                return None
            
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Get current price and order book
            ticker = await self.exchange.fetch_ticker(symbol)
            order_book = await self.exchange.fetch_order_book(symbol)
            
            return {
                'candles': df,
                'current_price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'order_book': order_book,
                'timestamp': datetime.now().timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def enter_trade(self, signal: EnhancedSignal, market_data: Dict):
        """Enter a new trade based on signal"""
        try:
            symbol = signal.symbol
            current_price = market_data['current_price']
            
            # Calculate position size using risk manager
            position_size = self.risk_manager.calculate_position_size(
                current_price, signal.stop_loss, symbol
            )
            
            if position_size <= 0:
                self.logger.debug(f"Position size too small for {symbol}: {position_size}")
                return
            
            # Adjust position size based on aggressiveness
            aggressiveness = self.risk_manager.get_trading_aggressiveness()
            position_size *= aggressiveness
            
            # Check minimum order size
            min_order_size = self.config.get('min_order_size', 10)
            if position_size * current_price < min_order_size:
                self.logger.debug(f"Order size below minimum for {symbol}")
                return
            
            # Execute order
            if signal.action == "BUY":
                order = await self.exchange.create_market_buy_order(symbol, position_size)
            else:  # SELL
                order = await self.exchange.create_market_sell_order(symbol, position_size)
            
            # Record position
            self.active_positions[symbol] = {
                'side': signal.action.lower(),
                'entry_price': current_price,
                'size': position_size,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'entry_time': datetime.now(),
                'signal_confidence': signal.confidence,
                'signal_reason': signal.reason
            }
            
            self.logger.info(
                f"Entered {signal.action} position for {symbol}: "
                f"Size: {position_size:.6f}, Price: {current_price:.2f}, "
                f"Confidence: {signal.confidence:.2f}, Reason: {signal.reason}"
            )
            
            # Save to database if available
            if self.db_manager:
                await self.db_manager.save_trade({
                    'symbol': symbol,
                    'side': signal.action,
                    'entry_price': current_price,
                    'size': position_size,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'timestamp': datetime.now(),
                    'confidence': signal.confidence,
                    'reason': signal.reason
                })
                
        except Exception as e:
            self.logger.error(f"Error entering trade for {signal.symbol}: {e}")
    
    async def monitor_position(self, symbol: str, market_data: Dict):
        """Monitor and manage existing position"""
        try:
            position = self.active_positions[symbol]
            current_price = market_data['current_price']
            
            # Check exit conditions
            should_exit = False
            exit_reason = ""
            pnl = 0.0
            
            if position['side'] == 'buy':
                pnl = (current_price - position['entry_price']) * position['size']
                if current_price <= position['stop_loss']:
                    should_exit = True
                    exit_reason = "Stop loss"
                elif current_price >= position['take_profit']:
                    should_exit = True
                    exit_reason = "Take profit"
            else:  # sell
                pnl = (position['entry_price'] - current_price) * position['size']
                if current_price >= position['stop_loss']:
                    should_exit = True
                    exit_reason = "Stop loss"
                elif current_price <= position['take_profit']:
                    should_exit = True
                    exit_reason = "Take profit"
            
            # Check trailing stop or other exit conditions
            if await self.check_additional_exit_conditions(symbol, position, market_data):
                should_exit = True
                exit_reason = "Additional exit condition"
            
            if should_exit:
                await self.exit_trade(symbol, exit_reason, pnl)
                
        except Exception as e:
            self.logger.error(f"Error monitoring position for {symbol}: {e}")
    
    async def check_additional_exit_conditions(self, symbol: str, position: Dict, market_data: Dict) -> bool:
        """Check additional exit conditions like time-based exits or signal reversal"""
        # Time-based exit (e.g., close position after 4 hours)
        position_age = datetime.now() - position['entry_time']
        if position_age.total_seconds() > 4 * 3600:  # 4 hours
            self.logger.info(f"Closing position for {symbol} due to time limit")
            return True
        
        # Check for signal reversal
        current_signal = self.strategy.generate_signal(symbol, market_data)
        if (current_signal.action != "HOLD" and 
            current_signal.action != position['side'].upper() and
            current_signal.confidence > self.strategy.min_confidence):
            self.logger.info(f"Closing position for {symbol} due to signal reversal")
            return True
        
        return False
    
    async def exit_trade(self, symbol: str, reason: str, pnl: float):
        """Exit a trade"""
        try:
            position = self.active_positions[symbol]
            
            # Execute exit order
            if position['side'] == 'buy':
                await self.exchange.create_market_sell_order(symbol, position['size'])
            else:
                await self.exchange.create_market_buy_order(symbol, position['size'])
            
            # Update risk manager
            is_win = pnl > 0
            self.risk_manager.update_after_trade(pnl, is_win)
            
            # Log exit
            self.logger.info(
                f"Exited {position['side']} position for {symbol}: "
                f"PnL: {pnl:.2f}, Reason: {reason}"
            )
            
            # Save to database if available
            if self.db_manager:
                await self.db_manager.update_trade_exit(symbol, {
                    'exit_price': await self.get_current_price(symbol),
                    'exit_time': datetime.now(),
                    'pnl': pnl,
                    'exit_reason': reason
                })
            
            # Remove from active positions
            del self.active_positions[symbol]
            
        except Exception as e:
            self.logger.error(f"Error exiting trade for {symbol}: {e}")
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return 0.0
    
    def _update_performance_metrics(self):
        """Update performance metrics"""
        metrics = self.risk_manager.get_performance_metrics()
        metrics['timestamp'] = datetime.now()
        metrics['active_positions'] = len(self.active_positions)
        
        self.performance_history.append(metrics)
        
        # Keep only last 1000 records
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def get_performance_report(self) -> Dict:
        """Get comprehensive performance report"""
        if not self.performance_history:
            return {}
        
        latest = self.performance_history[-1]
        
        return {
            'summary': latest,
            'recent_trades': self.performance_history[-10:],  # Last 10 updates
            'active_positions': list(self.active_positions.keys()),
            'risk_status': {
                'can_trade': not self.risk_manager.should_stop_trading(),
                'current_aggressiveness': self.risk_manager.get_trading_aggressiveness(),
                'consecutive_losses': self.risk_manager.consecutive_losses
            }
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        
        # Close all open positions
        for symbol in list(self.active_positions.keys()):
            try:
                current_price = await self.get_current_price(symbol)
                position = self.active_positions[symbol]
                
                if position['side'] == 'buy':
                    pnl = (current_price - position['entry_price']) * position['size']
                else:
                    pnl = (position['entry_price'] - current_price) * position['size']
                
                await self.exit_trade(symbol, "Bot shutdown", pnl)
            except Exception as e:
                self.logger.error(f"Error closing position for {symbol} during cleanup: {e}")
        
        # Save ML model
        self.strategy.save_model()
        
        self.logger.info("Enhanced Trading Bot shutdown complete")