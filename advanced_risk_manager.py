import numpy as np
from datetime import datetime
import logging

class AdvancedRiskManager:
    def __init__(self, config):
        self.config = config
        risk_config = config.get('risk_management', {})
        
        self.initial_balance = config.get('initial_balance', 1000)
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        
        self.risk_per_trade = risk_config.get('risk_per_trade', 0.02)
        self.max_drawdown = risk_config.get('max_drawdown', 0.15)
        
        self.total_trades = 0
        self.winning_trades = 0
        self.consecutive_losses = 0
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, entry_price, stop_loss, symbol):
        """Calculate position size based on risk"""
        risk_amount = self.current_balance * self.risk_per_trade
        price_risk = abs(entry_price - stop_loss) / entry_price
        
        if price_risk == 0:
            return 0
            
        position_value = risk_amount / price_risk
        position_size = position_value / entry_price
        
        # Adjust for consecutive losses
        if self.consecutive_losses >= 3:
            position_size *= 0.5
            
        return position_size
    
    def update_after_trade(self, pnl, is_win):
        """Update after trade"""
        self.current_balance += pnl
        self.total_trades += 1
        
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
            
        if is_win:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
    
    def should_stop_trading(self):
        """Check if should stop trading"""
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        return drawdown >= self.max_drawdown or self.consecutive_losses >= 10
    
    def get_performance_metrics(self):
        """Get performance metrics"""
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        
        return {
            'current_balance': self.current_balance,
            'total_trades': self.total_trades,
            'win_rate': win_rate * 100,
            'consecutive_losses': self.consecutive_losses,
            'drawdown': drawdown * 100
        }