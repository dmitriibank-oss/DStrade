import pandas as pd
import numpy as np
import logging
from typing import Dict, List

class PortfolioManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.performance_history = []
        
    def calculate_position_size(self, pair: str, account_balance: float) -> float:
        """Расчет размера позиции на основе риска"""
        pair_settings = self.config.get_pair_settings(pair)
        base_amount = pair_settings['trade_amount']
        
        # Корректировка на основе доступного баланса
        max_position_value = account_balance * self.config.MAX_POSITION_SIZE
        current_price = self.get_current_price(pair)  # Нужно реализовать получение цены
        
        if current_price > 0:
            calculated_amount = max_position_value / current_price
            # Используем минимальное значение между базовым и рассчитанным
            final_amount = min(base_amount, calculated_amount)
            return final_amount
        else:
            return base_amount
            
    def get_current_price(self, pair: str) -> float:
        """Получение текущей цены пары (заглушка)"""
        # В реальной реализации нужно получить цену от API
        return 0
        
    def analyze_asset_correlation(self, price_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """Анализ корреляции между активами"""
        if len(price_data) < 2:
            return pd.DataFrame()
            
        # Создание DataFrame с ценами
        df = pd.DataFrame(price_data)
        correlation_matrix = df.corr()
        
        return correlation_matrix
        
    def optimize_portfolio_allocation(self, correlations: pd.DataFrame, signals: Dict[str, Dict]) -> Dict[str, float]:
        """Оптимизация распределения портфеля на основе корреляций и сигналов"""
        allocation = {}
        
        # Простая стратегия: уменьшаем вес активов с высокой корреляцией
        buy_signals = [pair for pair, signal in signals.items() if signal.get('signal') == 'BUY']
        
        for pair in buy_signals:
            if pair in correlations.columns:
                # Средняя корреляция с другими активами
                avg_correlation = correlations[pair].mean()
                # Вес обратно пропорционален корреляции
                weight = max(0.1, 1 - avg_correlation)
                allocation[pair] = weight
            else:
                allocation[pair] = 1.0
                
        # Нормализация весов
        total_weight = sum(allocation.values())
        if total_weight > 0:
            allocation = {k: v/total_weight for k, v in allocation.items()}
            
        return allocation
        
    def log_performance(self, cycle_data: Dict):
        """Логирование производительности портфеля"""
        self.performance_history.append(cycle_data)
        
        # Сохранение в файл
        if len(self.performance_history) % 10 == 0:  # Каждые 10 циклов
            df = pd.DataFrame(self.performance_history)
            df.to_csv('portfolio_performance.csv', index=False)