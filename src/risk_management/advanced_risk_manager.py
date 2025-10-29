import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging
from enum import Enum

class RiskLevel(Enum):
    LOW = 0.1
    MEDIUM = 0.2
    HIGH = 0.3

class AdvancedRiskManager:
    def __init__(self, config: Dict):
        self.config = config
        self.initial_balance = config.get('initial_balance', 1000)
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.total_trades = 0
        self.winning_trades = 0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        self.drawdown = 0.0
        self.max_drawdown = 0.0
        
        # Risk parameters
        self.base_risk_per_trade = config.get('risk_per_trade', 0.02)
        self.max_daily_loss = config.get('max_daily_loss', 0.05)
        self.max_total_drawdown = config.get('max_drawdown', 0.15)
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, symbol: str) -> float:
        """Calculate position size based on risk parameters"""
        self._reset_daily_if_needed()
        
        # Calculate risk amount
        risk_amount = self.current_balance * self.base_risk_per_trade * self._get_risk_multiplier()
        
        # Adjust for consecutive losses
        if self.consecutive_losses >= 3:
            risk_amount *= 0.5
        elif self.consecutive_losses >= 5:
            risk_amount *= 0.25
        
        # Adjust for current drawdown
        current_drawdown = self._calculate_current_drawdown()
        if current_drawdown > 0.05:
            risk_amount *= 0.7
        elif current_drawdown > 0.1:
            risk_amount *= 0.4
        
        # Calculate position size
        price_risk_pct = abs(entry_price - stop_loss) / entry_price
        if price_risk_pct == 0:
            return 0
            
        position_value = risk_amount / price_risk_pct
        position_size = position_value / entry_price
        
        # Apply symbol-specific limits
        symbol_config = self.config.get('symbols', {}).get(symbol, {})
        max_position_size = symbol_config.get('max_position_size', float('inf'))
        min_position_size = symbol_config.get('min_position_size', 0)
        
        position_size = max(min_position_size, min(position_size, max_position_size))
        
        # Check daily loss limit
        if abs(self.daily_pnl) >= self.current_balance * self.max_daily_loss:
            self.logger.warning("Daily loss limit reached, reducing position size to 0")
            return 0
            
        return position_size
    
    def update_after_trade(self, pnl: float, is_win: bool):
        """Update risk parameters after a trade"""
        self.current_balance += pnl
        self.daily_pnl += pnl
        self.total_trades += 1
        
        # Update peak balance and drawdown
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        current_drawdown = self._calculate_current_drawdown()
        self.drawdown = current_drawdown
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # Update win/loss stats
        if is_win:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.max_consecutive_losses = max(self.max_consecutive_losses, self.consecutive_losses)
    
    def should_stop_trading(self) -> bool:
        """Check if trading should be stopped due to risk limits"""
        if self.drawdown >= self.max_total_drawdown:
            self.logger.error(f"Max drawdown limit reached: {self.drawdown:.2%}")
            return True
            
        if self.consecutive_losses >= 10:
            self.logger.error(f"Too many consecutive losses: {self.consecutive_losses}")
            return True
            
        if abs(self.daily_pnl) >= self.current_balance * self.max_daily_loss:
            self.logger.error(f"Daily loss limit reached: {self.daily_pnl:.2f}")
            return True
            
        return False
    
    def get_trading_aggressiveness(self) -> float:
        """Get current trading aggressiveness multiplier"""
        aggressiveness = 1.0
        
        # Reduce aggressiveness during drawdown
        if self.drawdown > 0.05:
            aggressiveness *= 0.8
        if self.drawdown > 0.1:
            aggressiveness *= 0.6
            
        # Increase aggressiveness during winning streaks with good win rate
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        if win_rate > 0.6 and self.consecutive_losses == 0:
            aggressiveness *= 1.2
            
        return max(0.1, min(2.0, aggressiveness))
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown from peak"""
        if self.peak_balance == 0:
            return 0.0
        return (self.peak_balance - self.current_balance) / self.peak_balance
    
    def _get_risk_multiplier(self) -> float:
        """Get dynamic risk multiplier based on performance"""
        base_multiplier = 1.0
        
        # Adjust based on win rate
        if self.total_trades > 10:
            win_rate = self.winning_trades / self.total_trades
            if win_rate > 0.6:
                base_multiplier *= 1.2
            elif win_rate < 0.4:
                base_multiplier *= 0.8
        
        # Adjust based on current streak
        if self.consecutive_losses >= 2:
            base_multiplier *= 0.7
            
        return base_multiplier
    
    def _reset_daily_if_needed(self):
        """Reset daily PnL if it's a new day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        total_return = (self.current_balance - self.initial_balance) / self.initial_balance
        
        return {
            'current_balance': self.current_balance,
            'total_return_pct': total_return * 100,
            'win_rate': win_rate * 100,
            'total_trades': self.total_trades,
            'current_drawdown': self.drawdown * 100,
            'max_drawdown': self.max_drawdown * 100,
            'consecutive_losses': self.consecutive_losses,
            'max_consecutive_losses': self.max_consecutive_losses,
            'daily_pnl': self.daily_pnl,
            'aggressiveness': self.get_trading_aggressiveness()
        }