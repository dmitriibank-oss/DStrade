import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__)))

from server.api.bybit import BybitAPI

def close_all_positions():
    """Закрытие всех открытых позиций"""
    load_dotenv()
    
    api = BybitAPI()
    
    print("🚨 Closing All Positions...")
    print("="*50)
    
    # Получаем все позиции
    positions = api.get_positions(category="linear")
    if positions and 'result' in positions and 'list' in positions['result']:
        open_positions = [p for p in positions['result']['list'] if float(p.get('size', 0)) > 0]
        
        if not open_positions:
            print("✅ No open positions to close")
            return
        
        for pos in open_positions:
            symbol = pos['symbol']
            size = float(pos['size'])
            side = pos['side']
            
            print(f"Closing {symbol}: {size} units ({side})")
            
            # Определяем противоположную сторону для закрытия
            close_side = 'Sell' if side == 'Buy' else 'Buy'
            
            result = api.place_order(
                category='linear',
                symbol=symbol,
                side=close_side,
                order_type='Market',
                qty=size
            )
            
            if result:
                print(f"✅ Successfully closed {symbol}")
            else:
                print(f"❌ Failed to close {symbol}")
    else:
        print("❌ Failed to get positions")

if __name__ == "__main__":
    confirm = input("Are you sure you want to close ALL positions? (yes/no): ")
    if confirm.lower() == 'yes':
        close_all_positions()
    else:
        print("Operation cancelled")