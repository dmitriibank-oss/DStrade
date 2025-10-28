import json
import pandas as pd
from datetime import datetime
from config.config import Config

class PerformanceTracker:
    def __init__(self):
        self.trades = []
        self.performance_data = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0
        }
        
    def record_trade(self, trade_data):
        """Запись данных о сделке"""
        self.trades.append({
            **trade_data,
            'timestamp': datetime.now().isoformat()
        })
        self._update_performance()
        
        if Config.SAVE_TRADES:
            self._save_trades()
    
    def _update_performance(self):
        """Обновление метрик производительности"""
        if not self.trades:
            return
        
        df = pd.DataFrame(self.trades)
        
        # Базовые метрики
        self.performance_data['total_trades'] = len(df)
        self.performance_data['winning_trades'] = len(df[df['pnl'] > 0])
        self.performance_data['losing_trades'] = len(df[df['pnl'] < 0])
        self.performance_data['total_pnl'] = df['pnl'].sum()
        
        # Win Rate
        if self.performance_data['total_trades'] > 0:
            self.performance_data['win_rate'] = (
                self.performance_data['winning_trades'] / self.performance_data['total_trades']
            )
        
        # Profit Factor
        gross_profit = df[df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
        if gross_loss > 0:
            self.performance_data['profit_factor'] = gross_profit / gross_loss
        
        # Максимальная просадка
        if 'balance_after' in df.columns:
            df['peak'] = df['balance_after'].cummax()
            df['drawdown'] = (df['peak'] - df['balance_after']) / df['peak']
            self.performance_data['max_drawdown'] = df['drawdown'].max()
    
    def _save_trades(self):
        """Сохранение сделок в файл"""
        try:
            with open(Config.TRADE_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.trades, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving trades: {e}")
    
    def generate_report(self):
        """Генерация отчета"""
        report = {
            **self.performance_data,
            'timestamp': datetime.now().isoformat(),
            'analysis': self._analyze_performance()
        }
        return report
    
    def _analyze_performance(self):
        """Анализ производительности и рекомендации"""
        analysis = []
        
        if self.performance_data['total_trades'] < 10:
            analysis.append("Недостаточно данных для анализа. Нужно больше сделок.")
            return analysis
        
        # Анализ Win Rate
        win_rate = self.performance_data['win_rate']
        if win_rate < 0.4:
            analysis.append("Низкий Win Rate. Рассмотрите ужесточение критериев входа.")
        elif win_rate > 0.6:
            analysis.append("Высокий Win Rate. Возможно, можно увеличить размер позиций.")
        
        # Анализ Profit Factor
        pf = self.performance_data['profit_factor']
        if pf < 1.0:
            analysis.append("Profit Factor ниже 1.0 - стратегия убыточна.")
        elif pf > 2.0:
            analysis.append("Отличный Profit Factor! Стратегия работает хорошо.")
        
        # Анализ просадки
        drawdown = self.performance_data['max_drawdown']
        if drawdown > 0.1:
            analysis.append(f"Большая просадка ({drawdown:.1%}). Увеличьте стоп-лоссы или уменьшите риск.")
        
        return analysis
    
    def get_strategy_performance(self):
        """Анализ производительности по типам стратегий"""
        if not self.trades:
            return {}
        
        df = pd.DataFrame(self.trades)
        
        # Группировка по символам (если есть информация о стратегии)
        strategy_stats = {}
        if 'symbol' in df.columns:
            for symbol in df['symbol'].unique():
                symbol_trades = df[df['symbol'] == symbol]
                strategy_stats[symbol] = {
                    'trades': len(symbol_trades),
                    'win_rate': len(symbol_trades[symbol_trades['pnl'] > 0]) / len(symbol_trades),
                    'total_pnl': symbol_trades['pnl'].sum(),
                    'avg_pnl': symbol_trades['pnl'].mean()
                }
        
        return strategy_stats