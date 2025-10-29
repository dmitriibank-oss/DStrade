#!/usr/bin/env python3
"""
Debug script to understand config structure
"""

import sys
from pathlib import Path

# Add the root directory to Python path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

try:
    from config import Config
    
    print("🔍 Analyzing Config structure...")
    
    config_obj = Config()
    print(f"Config object type: {type(config_obj)}")
    print(f"Config object: {config_obj}")
    
    # Try different methods to access config
    print("\n📋 Trying to access config data:")
    
    # Method 1: Check if it has get_config method
    if hasattr(config_obj, 'get_config'):
        print("✅ Has get_config method")
        try:
            config_data = config_obj.get_config()
            print(f"get_config() returned: {type(config_data)}")
            print(f"Keys: {list(config_data.keys()) if hasattr(config_data, 'keys') else 'No keys'}")
        except Exception as e:
            print(f"❌ get_config() failed: {e}")
    else:
        print("❌ No get_config method")
    
    # Method 2: Check if it has config attribute
    if hasattr(config_obj, 'config'):
        print("✅ Has config attribute")
        config_data = config_obj.config
        print(f"config attribute type: {type(config_data)}")
        print(f"Keys: {list(config_data.keys()) if hasattr(config_data, 'keys') else 'No keys'}")
    else:
        print("❌ No config attribute")
    
    # Method 3: Try vars()
    try:
        config_vars = vars(config_obj)
        print("✅ vars() worked")
        print(f"vars() keys: {list(config_vars.keys())}")
        print(f"vars() values: {config_vars}")
    except Exception as e:
        print(f"❌ vars() failed: {e}")
    
    # Method 4: Check if it's a dict
    if isinstance(config_obj, dict):
        print("✅ Config is a dictionary")
        print(f"Dictionary keys: {list(config_obj.keys())}")
    else:
        print("❌ Config is not a dictionary")
        
    # Method 5: Check dir
    print(f"\n📖 All attributes: {[attr for attr in dir(config_obj) if not attr.startswith('_')]}")
    
except ImportError as e:
    print(f"❌ Cannot import Config: {e}")
except Exception as e:
    print(f"❌ Error: {e}")