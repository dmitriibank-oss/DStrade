import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional

class RiskManager:
    def __init__(self, config, api):
        self.config = config
        self.api = api
        self.logger = logging.getLogger(__name__)
        
    def calculate_position_size(self, pair: str, current_price: float) -> float:
        """Автоматический расчет размера позиции на основе риска для 100 USDT"""
        try:
            # Получаем баланс счета
            balance_data = self.api.get_account_balance(self.config.ACCOUNT_TYPE)
            if not balance_data:
                return self._get_default_amount(pair)
                
            # Извлекаем доступный баланс USDT
            available_balance = 0
            if 'result' in balance_data and 'list' in balance_data['result']:
                account_info = balance_data['result']['list'][0]
                coins = account_info.get('coin', [])
                for coin in coins:
                    if coin.get('coin') == 'USDT':
                        available_balance = float(coin.get('availableToWithdraw', 0))
                        break
            
            if available_balance <= 0:
                self.logger.warning(f"No available USDT balance, using default amount for {pair}")
                return self._get_default_amount(pair)
            
            # Расчет максимальной суммы на сделку (5% от баланса для тестинга)
            max_trade_value = available_balance * 0.05
            
            # Используем BASE_TRADE_AMOUNT (100 USDT), но не более 5% от баланса
            target_trade_value = min(self.config.BASE_TRADE_AMOUNT, max_trade_value)
            
            # Получаем индивидуальные настройки пары
            pair_settings = self.config.get_pair_settings(pair)
            base_amount = pair_settings['trade_amount']
            
            # Рассчитываем стоимость базовой позиции
            base_position_value = base_amount * current_price
            
            # Если базовая позиция меньше целевой, увеличиваем количество
            if base_position_value < target_trade_value:
                adjusted_amount = target_trade_value / current_price
                self.logger.info(f"Increased position size for {pair}: {base_amount} -> {adjusted_amount:.6f} (target: {target_trade_value:.2f} USDT)")
                return adjusted_amount
            else:
                # Если базовая позиция больше целевой, используем базовую
                self.logger.info(f"Using base position size for {pair}: {base_amount} (~{base_position_value:.2f} USDT)")
                return base_amount
                
        except Exception as e:
            self.logger.error(f"Error calculating position size for {pair}: {e}")
            return self._get_default_amount(pair)
    
    def _get_default_amount(self, pair: str) -> float:
        """Получение размера по умолчанию для пары"""
        pair_settings = self.config.get_pair_settings(pair)
        return pair_settings['trade_amount']
    
    def should_skip_trade(self, pair: str, signal: str, current_volatility: float) -> bool:
        """Проверка, стоит ли пропускать сделку из-за высокого риска"""
        # Пропускаем если волатильность слишком высокая
        if current_volatility > 20.0:  # 20% волатильность для тестинга
            self.logger.warning(f"Skipping {pair} trade due to high volatility: {current_volatility:.2f}%")
            return True
            
        # Пропускаем если баланс меньше 200 USDT (минимальный для 2 сделок)
        balance_data = self.api.get_account_balance(self.config.ACCOUNT_TYPE)
        if balance_data and 'result' in balance_data and 'list' in balance_data['result']:
            account_info = balance_data['result']['list'][0]
            coins = account_info.get('coin', [])
            for coin in coins:
                if coin.get('coin') == 'USDT':
                    available_balance = float(coin.get('availableToWithdraw', 0))
                    if available_balance < 200:
                        self.logger.warning(f"Skipping {pair} trade due to low balance: {available_balance:.2f} USDT")
                        return True
                    break
            
        return False
        
    def get_trade_value_info(self, pair: str, amount: float, current_price: float) -> Dict:
        """Получение информации о стоимости сделки"""
        position_value = amount * current_price
        leverage = self.config.get_pair_settings(pair)['leverage']
        
        return {
            'pair': pair,
            'amount': amount,
            'current_price': current_price,
            'position_value_usdt': position_value,
            'leverage': leverage,
            'effective_exposure': position_value * leverage
        }