class TradeCalculator:
    """Калькулятор для ручной проверки размеров позиций"""
    
    @staticmethod
    def calculate_position_size(pair: str, target_usdt: float, current_price: float) -> float:
        """Расчет количества для целевой суммы в USDT"""
        return target_usdt / current_price
    
    @staticmethod
    def print_expected_trades(config, current_prices: Dict[str, float]):
        """Печать ожидаемых размеров сделок"""
        print("\n" + "="*60)
        print("EXPECTED TRADE SIZES (Based on current prices)")
        print("="*60)
        
        total_risk = 0
        
        for pair in config.TRADING_PAIRS:
            if pair in current_prices:
                price = current_prices[pair]
                pair_settings = config.get_pair_settings(pair)
                base_amount = pair_settings['trade_amount']
                position_value = base_amount * price
                leverage = pair_settings['leverage']
                
                print(f"\n{pair}:")
                print(f"  Current Price: ${price:.2f}")
                print(f"  Base Amount: {base_amount}")
                print(f"  Expected Position: ${position_value:.2f} USDT")
                print(f"  Leverage: {leverage}x")
                print(f"  Effective Exposure: ${position_value * leverage:.2f}")
                
                total_risk += position_value
        
        print(f"\nTotal Expected Risk: ${total_risk:.2f} USDT")
        print("="*60)