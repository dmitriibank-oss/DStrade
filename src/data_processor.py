import pandas as pd
import ta
import numpy as np
from ta.trend import ADXIndicator, IchimokuIndicator
from ta.momentum import StochasticOscillator

class DataProcessor:
    @staticmethod
    def calculate_technical_indicators(df):
        """Расчет технических индикаторов"""
        try:
            # RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # EMA
            df['ema_short'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
            df['ema_long'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_hist'] = macd.macd_diff()
            
            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['bb_upper'] = bollinger.bollinger_hband()
            df['bb_middle'] = bollinger.bollinger_mavg()
            df['bb_lower'] = bollinger.bollinger_lband()
            
            # Volume SMA
            df['volume_sma'] = ta.trend.SMAIndicator(df['volume'], window=20).sma_indicator()
            
            return df
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return df
    
    @staticmethod
    def calculate_advanced_indicators(df):
        """Расчет продвинутых индикаторов"""
        try:
            # ADX (Average Directional Index)
            adx_i = ADXIndicator(df['high'], df['low'], df['close'], window=14)
            df['adx'] = adx_i.adx()
            df['plus_di'] = adx_i.adx_pos()
            df['minus_di'] = adx_i.adx_neg()
            
            # Ichimoku Cloud
            ichimoku = IchimokuIndicator(df['high'], df['low'])
            df['tenkan_sen'] = ichimoku.ichimoku_conversion_line()
            df['kijun_sen'] = ichimoku.ichimoku_base_line()
            df['senkou_span_a'] = ichimoku.ichimoku_a()
            df['senkou_span_b'] = ichimoku.ichimoku_b()
            
            # Stochastic
            stoch = StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # ATR (Average True Range)
            df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
            
            # Williams %R
            df['williams_r'] = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close'], lbp=14).williams_r()
            
            # CCI (Commodity Channel Index)
            df['cci'] = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], window=20).cci()
            
            return df
        except Exception as e:
            print(f"Error calculating advanced indicators: {e}")
            return df
    
    @staticmethod
    def detect_support_resistance(df, window=20):
        """Обнаружение уровней поддержки и сопротивления"""
        try:
            df['resistance'] = df['high'].rolling(window=window).max()
            df['support'] = df['low'].rolling(window=window).min()
            
            # Динамические уровни поддержки/сопротивления
            df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
            df['r1'] = 2 * df['pivot'] - df['low']
            df['s1'] = 2 * df['pivot'] - df['high']
            
            return df
        except Exception as e:
            print(f"Error detecting support/resistance: {e}")
            return df
    
    @staticmethod
    def calculate_volatility(df, period=20):
        """Расчет волатильности"""
        try:
            df['returns'] = df['close'].pct_change()
            df['volatility'] = df['returns'].rolling(window=period).std()
            
            # Historical Volatility (годовая)
            df['hv_20'] = df['returns'].rolling(window=20).std() * np.sqrt(365)
            
            return df
        except Exception as e:
            print(f"Error calculating volatility: {e}")
            return df
    
    @staticmethod
    def add_price_features(df):
        """Добавление дополнительных фич цены"""
        try:
            # Процентное изменение
            df['price_change_pct'] = df['close'].pct_change()
            df['price_change_5'] = df['close'].pct_change(5)
            df['price_change_10'] = df['close'].pct_change(10)
            
            # High-Low диапазон
            df['high_low_range'] = (df['high'] - df['low']) / df['close']
            
            # Open-Close диапазон
            df['open_close_range'] = (df['close'] - df['open']) / df['open']
            
            # Скользящие средние
            df['sma_5'] = ta.trend.SMAIndicator(df['close'], window=5).sma_indicator()
            df['sma_10'] = ta.trend.SMAIndicator(df['close'], window=10).sma_indicator()
            df['sma_20'] = ta.trend.SMAIndicator(df['close'], window=20).sma_indicator()
            df['sma_50'] = ta.trend.SMAIndicator(df['close'], window=50).sma_indicator()
            
            # Momentum features
            df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
            df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
            
            # Volatility features
            df['volatility_5'] = df['returns'].rolling(5).std()
            df['volatility_10'] = df['returns'].rolling(10).std()
            
            return df
        except Exception as e:
            print(f"Error adding price features: {e}")
            return df