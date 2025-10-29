import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json

class StrategyMonitor:
    def __init__(self):
        self.signals_log = []
        
    def log_signal(self, signal, indicators, price, timestamp):
        """Логирование сигналов для анализа"""
        self.signals_log.append({
            'timestamp': timestamp,
            'signal': signal,
            'price': price,
            'indicators': indicators,
            'rsi': indicators.get('rsi'),
            'macd': indicators.get('macd'),
            'ema_20': indicators.get('ema_20'),
            'ema_50': indicators.get('ema_50')
        })
        
    def generate_report(self):
        """Генерация отчета о работе стратегии"""
        if not self.signals_log:
            return "No signals to report"
            
        df = pd.DataFrame(self.signals_log)
        
        print("=== Trading Strategy Report ===")
        print(f"Total signals: {len(df)}")
        print(f"BUY signals: {len(df[df['signal'] == 'BUY'])}")
        print(f"SELL signals: {len(df[df['signal'] == 'SELL'])}") 
        print(f"HOLD signals: {len(df[df['signal'] == 'HOLD'])}")
        
        # Анализ эффективности
        if len(df[df['signal'].isin(['BUY', 'SELL'])]) > 0:
            recent_trades = df[df['signal'].isin(['BUY', 'SELL'])].tail(10)
            print(f"\nRecent trades: {len(recent_trades)}")
            
        return df

# Глобальный монитор
monitor = StrategyMonitor()