#!/usr/bin/env python3
"""
Enhanced Main Entry Point for DStrade Bot - Final Version
"""

import time
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

# Add the root directory to Python path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Import required modules
try:
    from config import Config
    import ccxt
    
    # Import enhanced modules
    from advanced_risk_manager import AdvancedRiskManager
    from enhanced_ml_strategy import EnhancedMLStrategy
    from enhanced_bot import EnhancedTradingBot
    
    print("✅ All imports successful")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class EnhancedBotLauncher:
    def __init__(self, testnet=True, log_level="INFO"):
        self.testnet = testnet
        self.log_level = log_level
        self.config = {}
        self.exchange = None
        self.db_manager = None
        self.bot = None
        
        self.setup_directories()
        self.setup_logging()
        
    def setup_directories(self):
        """Create necessary directories"""
        directories = [
            'logs',
            'data/models',
            'data/market_data',
            'data/backtest_results'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created directory: {directory}")
            
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # File handler
        log_filename = f"logs/enhanced_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[file_handler, console_handler]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Enhanced bot logging setup complete")
        
    def load_configuration(self):
        """Load and enhance configuration from Config class"""
        try:
            config_obj = Config()
            
            # Extract all uppercase attributes from the config object
            config_dict = {}
            for attr in dir(config_obj):
                if not attr.startswith('_') and attr.isupper():
                    value = getattr(config_obj, attr)
                    config_dict[attr] = value
            
            self.config = config_dict
            self.logger.info(f"Loaded config with keys: {list(self.config.keys())}")
            
            # Map old config keys to new structure if needed
            # For example, convert SYMBOLS to symbols, etc.
            if 'SYMBOLS' in self.config and 'symbols' not in self.config:
                self.config['symbols'] = self.config['SYMBOLS']
            if 'INITIAL_BALANCE' in self.config and 'initial_balance' not in self.config:
                self.config['initial_balance'] = self.config['INITIAL_BALANCE']
            if 'TESTNET' in self.config and 'testnet' not in self.config:
                self.config['testnet'] = self.config['TESTNET']
            if 'BYBIT_API_KEY' in self.config and 'api_key' not in self.config:
                self.config['api_key'] = self.config['BYBIT_API_KEY']
            if 'BYBIT_API_SECRET' in self.config and 'api_secret' not in self.config:
                self.config['api_secret'] = self.config['BYBIT_API_SECRET']
            
            # Enhance with additional settings for improved trading
            enhanced_settings = {
                # Enhanced risk management
                'risk_management': {
                    'risk_per_trade': self.config.get('RISK_PER_TRADE', 0.02),
                    'max_daily_loss': self.config.get('DAILY_LOSS_LIMIT', 0.05),
                    'max_drawdown': self.config.get('MAX_DRAWDOWN', 0.15),
                    'dynamic_position_sizing': True,
                    'aggressiveness_adjustment': True,
                    'max_consecutive_losses': 10
                },
                
                # Enhanced strategy settings
                'enhanced_strategy': {
                    'min_confidence': self.config.get('MIN_SIGNAL_STRENGTH', 0.6),
                    'use_ml': True,
                    'max_open_positions': self.config.get('MAX_POSITIONS', 3),
                    'technical_indicators': {
                        'rsi_period': self.config.get('RSI_PERIOD', 14),
                        'macd_fast': 12,
                        'macd_slow': 26,
                        'macd_signal': 9,
                        'bb_period': 20,
                        'atr_period': 14,
                        'ema_short': self.config.get('EMA_SHORT', 20),
                        'ema_long': self.config.get('EMA_LONG', 50)
                    }
                },
                
                # Performance monitoring
                'performance_monitoring': {
                    'track_metrics': True,
                    'save_trade_history': self.config.get('SAVE_TRADES', True),
                    'generate_reports': True,
                    'report_interval': 1  # hours
                },
                
                # Execution settings
                'execution': {
                    'tick_interval': 30,  # seconds
                    'order_timeout': 30,
                    'max_retries': 3,
                    'slippage': 0.001,
                    'use_limit_orders': self.config.get('USE_LIMIT_ORDERS', False)
                }
            }
            
            # Merge enhanced settings with existing config
            for key, value in enhanced_settings.items():
                if key not in self.config:
                    self.config[key] = value
                elif isinstance(value, dict) and isinstance(self.config[key], dict):
                    # Merge dictionaries
                    self.config[key].update(value)
            
            # Ensure critical settings
            self.config['testnet'] = self.testnet
            
            if 'symbols' not in self.config:
                self.config['symbols'] = ['BTC/USDT', 'ETH/USDT']
                
            if 'initial_balance' not in self.config:
                self.config['initial_balance'] = 1000
                
            if 'api_key' not in self.config:
                self.config['api_key'] = 'testnet_key'
                
            if 'api_secret' not in self.config:
                self.config['api_secret'] = 'testnet_secret'
                
            self.logger.info("Configuration loaded and enhanced successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            # Create minimal config as fallback
            self.config = {
                'symbols': ['BTC/USDT', 'ETH/USDT'],
                'initial_balance': 1000,
                'testnet': True,
                'api_key': 'testnet_key',
                'api_secret': 'testnet_secret',
                'risk_management': {'risk_per_trade': 0.02},
                'enhanced_strategy': {'min_confidence': 0.6},
                'execution': {'tick_interval': 30}
            }
            self.logger.info("Using fallback minimal config")
            
    def initialize_exchange(self):
        """Initialize exchange connection"""
        try:
            # Get API credentials
            api_key = self.config.get('api_key', 'testnet_key')
            api_secret = self.config.get('api_secret', 'testnet_secret')
            
            exchange_config = {
                'apiKey': api_key,
                'secret': api_secret,
                'testnet': self.testnet,
                'sandbox': self.testnet,
                'enableRateLimit': True,
            }
            
            # Initialize exchange
            self.exchange = ccxt.bybit(exchange_config)
            
            # Set exchange options
            self.exchange.options['defaultType'] = 'spot'  # or 'future'
            
            self.logger.info("Exchange connection initialized successfully")
            
            # Test connection (non-blocking)
            asyncio.create_task(self.test_exchange_connection())
            
        except Exception as e:
            self.logger.error(f"Error initializing exchange: {e}")
            raise
            
    async def test_exchange_connection(self):
        """Test exchange connection"""
        try:
            # Fetch balance to test connection
            balance = await self.exchange.fetch_balance()
            self.logger.info(f"Exchange test successful. Total balance: {balance.get('total', {})}")
        except Exception as e:
            self.logger.warning(f"Exchange test failed: {e}. This might be normal for testnet.")
            
    def initialize_database(self):
        """Initialize database connection - placeholder for future use"""
        self.db_manager = None
        self.logger.info("Running without database (optional component)")
            
    def initialize_bot(self):
        """Initialize the enhanced trading bot"""
        try:
            self.bot = EnhancedTradingBot(
                exchange=self.exchange,
                config=self.config,
                db_manager=self.db_manager
            )
            self.logger.info("Enhanced trading bot initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing bot: {e}")
            raise
            
    def print_startup_info(self):
        """Print startup information"""
        print("\n" + "="*60)
        print("🚀 ENHANCED DSTRADE BOT - STARTING")
        print("="*60)
        print(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔧 Mode: {'TESTNET' if self.testnet else 'MAINNET'}")
        print(f"📊 Log Level: {self.log_level}")
        print(f"💰 Initial Balance: {self.config.get('initial_balance', 'N/A')}")
        
        symbols = self.config.get('symbols', [])
        if isinstance(symbols, list) and symbols:
            print(f"🎯 Trading Symbols: {', '.join(symbols[:3])}{'...' if len(symbols) > 3 else ''}")
        else:
            print(f"🎯 Trading Symbols: {symbols}")
            
        print(f"⏰ Tick Interval: {self.config.get('execution', {}).get('tick_interval', 30)}s")
        print("="*60)
        print()
        
    async def run(self):
        """Main execution method"""
        try:
            # Initialize components in correct order
            self.load_configuration()
            self.print_startup_info()
            self.initialize_exchange()
            self.initialize_database()
            self.initialize_bot()
            
            # Start the main bot
            self.logger.info("Starting enhanced trading bot main loop...")
            await self.bot.run()
            
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user (Ctrl+C)")
        except Exception as e:
            self.logger.error(f"Bot stopped with error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up resources...")
        
        try:
            if hasattr(self, 'bot') and self.bot:
                await self.bot.cleanup()
                
            if hasattr(self, 'exchange') and self.exchange:
                await self.exchange.close()
                
            self.logger.info("Cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Enhanced DStrade Trading Bot')
    
    parser.add_argument(
        '--testnet',
        action='store_true',
        default=True,
        help='Run in testnet mode (default: True)'
    )
    
    parser.add_argument(
        '--mainnet',
        action='store_true',
        default=False,
        help='Run in mainnet mode (use with caution!)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Override trading symbols (e.g., --symbols BTC/USDT ETH/USDT)'
    )
    
    return parser.parse_args()


def main():
# Test exchange connection - СИНХРОННЫЙ вызов
    try:
        exchange.fetch_balance()  # Убрать await
        logger.info("Exchange connection initialized successfully")
    except Exception as e:
        logger.warning(f"Exchange test failed: {e}. This might be normal for testnet.")


# Уберите asyncio.run()
if __name__ == "__main__":
    main()  # Просто вызываем main()