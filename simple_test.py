#!/usr/bin/env python3
"""
Simple test to check imports
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("🔍 Testing imports...")

# Test basic imports
try:
    from config import Config
    print("✅ config import OK")
    
    # Try to create config instance
    try:
        config_obj = Config()
        print("✅ Config() creation OK")
        
        # Try different ways to get config
        if hasattr(config_obj, 'get_config'):
            config = config_obj.get_config()
            print("✅ config_obj.get_config() OK")
        elif hasattr(config_obj, 'config'):
            config = config_obj.config
            print("✅ config_obj.config OK")
        else:
            config = config_obj
            print("✅ Using config_obj directly")
            
        print(f"Config keys: {list(config.keys()) if hasattr(config, 'keys') else 'No keys'}")
        
    except Exception as e:
        print(f"❌ Config creation error: {e}")
        
except ImportError as e:
    print(f"❌ config import failed: {e}")

# Test exchange imports
try:
    # Try different import methods
    try:
        from exchange.bybit import Bybit
        print("✅ from exchange.bybit import Bybit OK")
    except ImportError:
        try:
            from bybit import Bybit
            print("✅ from bybit import Bybit OK")
        except ImportError:
            try:
                import ccxt
                Bybit = ccxt.bybit
                print("✅ import ccxt OK")
            except ImportError as e:
                print(f"❌ All exchange imports failed: {e}")
                
except Exception as e:
    print(f"❌ Exchange import error: {e}")

# Test enhanced modules
try:
    from advanced_risk_manager import AdvancedRiskManager
    print("✅ AdvancedRiskManager import OK")
except ImportError as e:
    print(f"❌ AdvancedRiskManager import failed: {e}")

try:
    from enhanced_ml_strategy import EnhancedMLStrategy
    print("✅ EnhancedMLStrategy import OK")
except ImportError as e:
    print(f"❌ EnhancedMLStrategy import failed: {e}")

try:
    from enhanced_bot import EnhancedTradingBot
    print("✅ EnhancedTradingBot import OK")
except ImportError as e:
    print(f"❌ EnhancedTradingBot import failed: {e}")

print("\n🎯 Next steps:")
print("1. Make sure all 4 enhanced files are in the root directory")
print("2. Run: python simple_test.py")
print("3. Check which imports fail and fix them")