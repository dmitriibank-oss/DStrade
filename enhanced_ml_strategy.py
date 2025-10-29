import pandas as pd
import numpy as np
import logging

class EnhancedSignal:
    def __init__(self, symbol, action, confidence, entry_price, stop_loss, take_profit, reason=""):
        self.symbol = symbol
        self.action = action  # BUY, SELL, HOLD
        self.confidence = confidence
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reason = reason

class EnhancedMLStrategy:
    def __init__(self, config):
        self.config = config
        self.min_confidence = 0.6
        self.logger = logging.getLogger(__name__)
    
    def generate_signal(self, symbol, data):
        """Generate trading signal - simplified version"""
        try:
            df = data.get('candles', pd.DataFrame())
            current_price = data.get('current_price', 0)
            
            if df.empty or len(df) < 20:
                return EnhancedSignal(symbol, "HOLD", 0, current_price, 0, 0, "Insufficient data")
            
            # Simple RSI strategy for demo
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            volume_avg = df['volume'].tail(10).mean()
            current_volume = df['volume'].iloc[-1]
            
            if price_change > 0.01 and current_volume > volume_avg:
                return EnhancedSignal(symbol, "BUY", 0.7, current_price, 
                                    current_price * 0.98, current_price * 1.02, 
                                    "Price and volume uptrend")
            elif price_change < -0.01 and current_volume > volume_avg:
                return EnhancedSignal(symbol, "SELL", 0.7, current_price,
                                    current_price * 1.02, current_price * 0.98,
                                    "Price and volume downtrend")
            else:
                return EnhancedSignal(symbol, "HOLD", 0, current_price, 0, 0, "No clear signal")
                
        except Exception as e:
            self.logger.error(f"Error generating signal: {e}")
            return EnhancedSignal(symbol, "HOLD", 0, data.get('current_price', 0), 0, 0, f"Error: {e}")