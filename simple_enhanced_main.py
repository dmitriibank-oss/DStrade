#!/usr/bin/env python3
"""
Simple Enhanced Main - Minimal version
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config import Config
    from bybit import Bybit
    print("✓ Basic imports successful")
except ImportError as e:
    print(f"✗ Basic import error: {e}")
    sys.exit(1)

# Import enhanced modules directly
try:
    # Import from current directory
    from advanced_risk_manager import AdvancedRiskManager
    from enhanced_ml_strategy import EnhancedMLStrategy, EnhancedSignal
    from enhanced_bot import EnhancedTradingBot
    print("✓ Enhanced imports successful")
except ImportError:
    # Try from subdirectories
    try:
        from risk_management.advanced_risk_manager import AdvancedRiskManager
        from strategies.enhanced_ml_strategy import EnhancedMLStrategy, EnhancedSignal
        from trading.enhanced_bot import EnhancedTradingBot
        print("✓ Enhanced imports from subdirectories successful")
    except ImportError as e:
        print(f"✗ Enhanced import error: {e}")
        print("Please make sure enhanced modules are in correct locations")
        sys.exit(1)

async def main():
    """Simple main function"""
    print("🚀 Starting Enhanced Bot...")
    
    try:
        # Load config
        config_obj = Config()
        config = config_obj.get_config()
        
        # Initialize exchange
        exchange = Bybit({
            'apiKey': config.get('api_key'),
            'secret': config.get('api_secret'),
            'testnet': True
        })
        
        # Initialize bot
        bot = EnhancedTradingBot(exchange, config)
        
        print("✅ Bot initialized successfully")
        print("🔄 Starting main loop...")
        
        await bot.run()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())