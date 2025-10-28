import pandas as pd
import ta
import numpy as np

class DataProcessor:
    @staticmethod
    def calculate_technical_indicators(df):
        """Расчет технических индикаторов с использованием библиотеки ta"""
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
    def detect_support_resistance(df, window=20):
        """Обнаружение уровней поддержки и сопротивления"""
        try:
            df['resistance'] = df['high'].rolling(window=window).max()
            df['support'] = df['low'].rolling(window=window).min()
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
            
            # High-Low диапазон
            df['high_low_range'] = (df['high'] - df['low']) / df['close']
            
            # Open-Close диапазон
            df['open_close_range'] = (df['close'] - df['open']) / df['open']
            
            # Скользящие средние
            df['sma_5'] = ta.trend.SMAIndicator(df['close'], window=5).sma_indicator()
            df['sma_10'] = ta.trend.SMAIndicator(df['close'], window=10).sma_indicator()
            
            return df
        except Exception as e:
            print(f"Error adding price features: {e}")
            return df