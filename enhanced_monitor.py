import pandas as pd
import numpy as np
import logging
from datetime import datetime
import json
import os
from typing import Dict, List

class EnhancedMonitor:
    def __init__(self, config):
        self.config = config
        self.signals_history = []
        self.portfolio_history = []
        self.setup_logging()
        
    def setup_logging(self):
        self.logger = logging.getLogger('EnhancedMonitor')
        
    def log_trading_cycle(self, cycle_data: Dict):
        """Логирование данных торгового цикла"""
        cycle_data['timestamp'] = datetime.now().isoformat()
        self.signals_history.append(cycle_data)
        
        # Сохранение каждые 10 циклов
        if len(self.signals_history) % 10 == 0:
            self.save_history()
            
    def log_portfolio_status(self, portfolio_data: Dict):
        """Логирование статуса портфеля"""
        portfolio_data['timestamp'] = datetime.now().isoformat()
        self.portfolio_history.append(portfolio_data)
        
    def generate_detailed_report(self):
        """Генерация детального отчета"""
        if not self.signals_history:
            return "No trading data available"
            
        df = pd.DataFrame(self.signals_history)
        
        report = {
            'summary': {
                'total_cycles': len(df),
                'unique_pairs': df['pair'].nunique() if 'pair' in df.columns else 0,
                'start_time': df['timestamp'].min() if 'timestamp' in df.columns else 'N/A',
                'end_time': df['timestamp'].max() if 'timestamp' in df.columns else 'N/A'
            },
            'signals_analysis': self.analyze_signals(df),
            'performance_metrics': self.calculate_performance_metrics(df)
        }
        
        return report
        
    def analyze_signals(self, df: pd.DataFrame) -> Dict:
        """Анализ торговых сигналов"""
        if 'signal' not in df.columns:
            return {}
            
        signal_counts = df['signal'].value_counts().to_dict()
        
        # Анализ по парам
        pair_analysis = {}
        if 'pair' in df.columns:
            for pair in df['pair'].unique():
                pair_signals = df[df['pair'] == pair]['signal'].value_counts()
                pair_analysis[pair] = pair_signals.to_dict()
                
        return {
            'total_signals': signal_counts,
            'by_pair': pair_analysis
        }
        
    def calculate_performance_metrics(self, df: pd.DataFrame) -> Dict:
        """Расчет метрик производительности"""
        metrics = {}
        
        # Простые метрики (в реальной системе нужно учитывать PnL)
        if 'signal' in df.columns:
            total_signals = len(df)
            buy_signals = len(df[df['signal'] == 'BUY'])
            sell_signals = len(df[df['signal'] == 'SELL'])
            hold_signals = len(df[df['signal'] == 'HOLD'])
            
            metrics = {
                'signal_distribution': {
                    'buy_percentage': (buy_signals / total_signals) * 100,
                    'sell_percentage': (sell_signals / total_signals) * 100,
                    'hold_percentage': (hold_signals / total_signals) * 100
                },
                'activity_ratio': ((buy_signals + sell_signals) / total_signals) * 100
            }
            
        return metrics
        
    def save_history(self):
        """Сохранение истории в файлы"""
        try:
            # Создаем директорию для логов если не существует
            os.makedirs('logs', exist_ok=True)
            
            # Сохранение сигналов
            if self.signals_history:
                signals_df = pd.DataFrame(self.signals_history)
                signals_df.to_csv('logs/trading_signals_history.csv', index=False)
                
            # Сохранение портфеля
            if self.portfolio_history:
                portfolio_df = pd.DataFrame(self.portfolio_history)
                portfolio_df.to_csv('logs/portfolio_history.csv', index=False)
                
            self.logger.info("Trading history saved to files")
            
        except Exception as e:
            self.logger.error(f"Error saving history: {e}")
            
    def print_real_time_dashboard(self, current_signals: Dict, portfolio_summary: Dict):
        """Вывод реального дашборда в консоль"""
        print("\n" + "="*80)
        print(f"TRADING DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Сводка портфеля
        print(f"\n📊 PORTFOLIO SUMMARY:")
        print(f"   Active Trades: {portfolio_summary['active_trades']}/{portfolio_summary['max_concurrent_trades']}")
        print(f"   Total Pairs: {portfolio_summary['total_pairs']}")
        
        # Активные позиции
        active_positions = portfolio_summary['active_positions']
        if active_positions:
            print(f"\n🎯 ACTIVE POSITIONS:")
            for pair, position in active_positions.items():
                if position['size'] > 0:
                    print(f"   {pair}: {position['size']} units ({position['side']})")
        else:
            print(f"\n🎯 ACTIVE POSITIONS: None")
            
        # Текущие сигналы
        print(f"\n📈 CURRENT SIGNALS:")
        for pair, signal in current_signals.items():
            signal_icon = "🟢" if signal['signal'] == 'BUY' else "🔴" if signal['signal'] == 'SELL' else "⚪"
            # Обрезаем длинное описание для лучшего отображения
            reason = signal['reason'][:50] + "..." if len(signal['reason']) > 50 else signal['reason']
            print(f"   {signal_icon} {pair}: {signal['signal']} - {reason}")
            
        print("="*80)

# Глобальный монитор
enhanced_monitor = None

def init_enhanced_monitor(config):
    global enhanced_monitor
    enhanced_monitor = EnhancedMonitor(config)