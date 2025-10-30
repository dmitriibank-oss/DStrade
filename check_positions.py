import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__)))

from server.api.bybit import BybitAPI

def check_all_positions():
    """Проверка всех открытых позиций и ордеров"""
    load_dotenv()
    
    api = BybitAPI()
    
    print("🔍 Checking Portfolio Status...")
    print("="*50)
    
    # Проверка баланса
    balance = api.get_account_balance()
    if balance and 'result' in balance and 'list' in balance['result']:
        account_info = balance['result']['list'][0]
        print(f"💰 Account Equity: {account_info.get('totalEquity')} USDT")
        
        # USDT баланс
        coins = account_info.get('coin', [])
        for coin in coins:
            if coin.get('coin') == 'USDT':
                print(f"💵 USDT Wallet: {coin.get('walletBalance')}")
                print(f"📥 Available: {coin.get('availableToWithdraw', 'N/A')}")
                break
    
    print("\n🎯 Open Positions (All):")
    print("-" * 30)
    
    # Получаем все позиции с settleCoin=USDT
    positions = api.get_positions(category="linear")
    if positions and 'result' in positions and 'list' in positions['result']:
        open_positions = [p for p in positions['result']['list'] if float(p.get('size', 0)) > 0]
        
        if open_positions:
            for pos in open_positions:
                print(f"📈 {pos['symbol']}:")
                print(f"   Size: {pos['size']}")
                print(f"   Side: {pos['side']}")
                print(f"   Avg Price: {pos.get('avgPrice', 'N/A')}")
                print(f"   Unrealised PnL: {pos.get('unrealisedPnl', '0')}")
                print(f"   Leverage: {pos.get('leverage', 'N/A')}x")
                print(f"   Liq Price: {pos.get('liqPrice', 'N/A')}")
                print()
        else:
            print("   No open positions")
    else:
        print("   Failed to get positions or no positions")
    
    # Детальная проверка по каждой паре
    print("\n🔎 Detailed Position Check by Symbol:")
    print("-" * 40)
    
    trading_pairs = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT']
    for pair in trading_pairs:
        position = api.get_positions(category="linear", symbol=pair)
        if position and 'result' in position and 'list' in position['result']:
            pos_data = position['result']['list'][0] if position['result']['list'] else {}
            size = float(pos_data.get('size', 0))
            if size > 0:
                print(f"✅ {pair}: {size} ({pos_data.get('side')}) - PnL: {pos_data.get('unrealisedPnl', '0')}")
            else:
                print(f"❌ {pair}: No position")
        else:
            print(f"⚠️  {pair}: Failed to check")

    print("\n📊 Account Summary:")
    print("-" * 30)
    if balance and 'result' in balance and 'list' in balance['result']:
        account_info = balance['result']['list'][0]
        print(f"Total Equity: {account_info.get('totalEquity')} USDT")
        print(f"Total Margin: {account_info.get('totalMarginBalance')} USDT")
        print(f"Available Balance: {account_info.get('totalAvailableBalance')} USDT")

if __name__ == "__main__":
    check_all_positions()