import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import ta
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import logging

@dataclass
class EnhancedSignal:
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: int
    reason: str

class EnhancedMLStrategy:
    def __init__(self, config: Dict):
        self.config = config
        self.strategy_config = config.get('enhanced_strategy', {})
        self.indicators_config = self.strategy_config.get('technical_indicators', {})
        
        # ML model
        self.ml_model = None
        self.scaler = StandardScaler()
        self.is_model_trained = False
        self.model_path = "data/models/ml_model.joblib"
        self.scaler_path = "data/models/scaler.joblib"
        
        self.min_confidence = self.strategy_config.get('min_confidence', 0.6)
        self.required_confidence_diff = 0.1
        
        self.logger = logging.getLogger(__name__)
        
        # Try to load pre-trained model
        self._load_model()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive technical indicators"""
        if df.empty:
            return df
            
        # Price-based indicators
        df['rsi'] = ta.momentum.RSIIndicator(
            df['close'], 
            window=self.indicators_config.get('rsi_period', 14)
        ).rsi()
        
        df['macd'] = ta.trend.MACD(
            df['close'],
            window_slow=self.indicators_config.get('macd_slow', 26),
            window_fast=self.indicators_config.get('macd_fast', 12),
            window_sign=self.indicators_config.get('macd_signal', 9)
        ).macd()
        
        # Volatility indicators
        df['bb_upper'] = ta.volatility.BollingerBands(
            df['close'], 
            window=self.indicators_config.get('bb_period', 20)
        ).bollinger_hband()
        df['bb_lower'] = ta.volatility.BollingerBands(df['close']).bollinger_lband()
        df['bb_middle'] = ta.volatility.BollingerBands(df['close']).bollinger_mavg()
        
        df['atr'] = ta.volatility.AverageTrueRange(
            df['high'], df['low'], df['close'],
            window=self.indicators_config.get('atr_period', 14)
        ).average_true_range()
        
        # Trend indicators
        df['ema_short'] = ta.trend.EMAIndicator(
            df['close'], 
            window=self.indicators_config.get('ema_short', 20)
        ).ema_indicator()
        df['ema_long'] = ta.trend.EMAIndicator(
            df['close'], 
            window=self.indicators_config.get('ema_long', 50)
        ).ema_indicator()
        
        # Momentum indicators
        df['stoch_k'] = ta.momentum.StochasticOscillator(
            df['high'], df['low'], df['close']
        ).stoch()
        df['stoch_d'] = ta.momentum.StochasticOscillator(
            df['high'], df['low'], df['close']
        ).stoch_signal()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Derived features
        df['price_vs_ema20'] = (df['close'] - df['ema_short']) / df['ema_short']
        df['ema_cross'] = (df['ema_short'] - df['ema_long']) / df['ema_long']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['rsi_strength'] = df['rsi'] / 100 - 0.5
        
        return df
    
    def generate_features(self, df: pd.DataFrame) -> np.ndarray:
        """Generate features for ML model"""
        if len(df) < 50:
            return np.array([])
            
        feature_columns = [
            'rsi', 'macd', 'atr', 'stoch_k', 'stoch_d', 
            'price_vs_ema20', 'ema_cross', 'bb_position', 
            'volume_ratio', 'rsi_strength'
        ]
        
        # Add lagged features
        current_features = []
        for col in feature_columns:
            if col in df.columns:
                # Current value
                current_features.append(df[col].iloc[-1])
                # Lag 1
                if len(df) > 1:
                    current_features.append(df[col].iloc[-2])
                else:
                    current_features.append(0)
                # Rolling mean
                if len(df) > 5:
                    current_features.append(df[col].tail(5).mean())
                else:
                    current_features.append(df[col].mean())
        
        return np.array(current_features).reshape(1, -1)
    
    def generate_signal(self, symbol: str, data: Dict) -> EnhancedSignal:
        """Generate trading signal using combined approach"""
        df = pd.DataFrame(data['candles'])
        if df.empty:
            return EnhancedSignal(symbol, "HOLD", 0.0, data['current_price'], 0, 0, data['timestamp'], "No data")
        
        df_with_indicators = self.calculate_indicators(df)
        current_price = data['current_price']
        
        if len(df_with_indicators) < 20:
            return EnhancedSignal(symbol, "HOLD", 0.0, current_price, 0, 0, data['timestamp'], "Insufficient data")
        
        # Get signals from different methods
        technical_signal = self._technical_analysis(df_with_indicators, current_price, symbol)
        ml_signal = self._ml_analysis(df_with_indicators, current_price, symbol)
        
        # Combine signals
        final_signal = self._combine_signals(technical_signal, ml_signal, symbol, current_price, data['timestamp'])
        
        return final_signal
    
    def _technical_analysis(self, df: pd.DataFrame, current_price: float, symbol: str) -> EnhancedSignal:
        """Technical analysis based signal generation"""
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        
        buy_signals = 0
        sell_signals = 0
        reasons = []
        
        # RSI signals
        if last['rsi'] < 30 and prev['rsi'] >= 30:
            buy_signals += 1
            reasons.append("RSI oversold")
        elif last['rsi'] > 70 and prev['rsi'] <= 70:
            sell_signals += 1
            reasons.append("RSI overbought")
        
        # MACD signals
        if last['macd'] > 0 and prev['macd'] <= 0:
            buy_signals += 1
            reasons.append("MACD bullish crossover")
        elif last['macd'] < 0 and prev['macd'] >= 0:
            sell_signals += 1
            reasons.append("MACD bearish crossover")
        
        # Bollinger Bands signals
        if last['close'] <= last['bb_lower']:
            buy_signals += 1
            reasons.append("BB oversold")
        elif last['close'] >= last['bb_upper']:
            sell_signals += 1
            reasons.append("BB overbought")
        
        # EMA crossover
        if last['ema_short'] > last['ema_long'] and prev['ema_short'] <= prev['ema_long']:
            buy_signals += 1
            reasons.append("EMA bullish crossover")
        elif last['ema_short'] < last['ema_long'] and prev['ema_short'] >= prev['ema_long']:
            sell_signals += 1
            reasons.append("EMA bearish crossover")
        
        # Calculate confidence and determine signal
        total_signals = buy_signals + sell_signals
        if total_signals == 0:
            return EnhancedSignal(symbol, "HOLD", 0.0, current_price, 0, 0, df.index[-1].timestamp(), "No clear signals")
        
        confidence = min(0.8, (max(buy_signals, sell_signals) / 5) * 0.8)
        reason_str = ", ".join(reasons)
        
        if buy_signals > sell_signals:
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.02
            return EnhancedSignal(symbol, "BUY", confidence, current_price, stop_loss, take_profit, 
                                df.index[-1].timestamp(), reason_str)
        elif sell_signals > buy_signals:
            stop_loss = current_price * 1.02
            take_profit = current_price * 0.98
            return EnhancedSignal(symbol, "SELL", confidence, current_price, stop_loss, take_profit,
                                df.index[-1].timestamp(), reason_str)
        else:
            return EnhancedSignal(symbol, "HOLD", 0.0, current_price, 0, 0, df.index[-1].timestamp(), "Mixed signals")
    
    def _ml_analysis(self, df: pd.DataFrame, current_price: float, symbol: str) -> EnhancedSignal:
        """ML based signal generation"""
        if not self.is_model_trained:
            return EnhancedSignal(symbol, "HOLD", 0.0, current_price, 0, 0, df.index[-1].timestamp(), "ML model not trained")
        
        try:
            features = self.generate_features(df)
            if features.size == 0:
                return EnhancedSignal(symbol, "HOLD", 0.0, current_price, 0, 0, df.index[-1].timestamp(), "No features")
            
            # Scale features and predict
            features_scaled = self.scaler.transform(features)
            prediction = self.ml_model.predict(features_scaled)[0]
            probability = np.max(self.ml_model.predict_proba(features_scaled))
            
            if probability > self.min_confidence:
                if prediction == 1:  # BUY
                    return EnhancedSignal(symbol, "BUY", probability, current_price, 
                                        current_price * 0.98, current_price * 1.02, 
                                        df.index[-1].timestamp(), "ML prediction")
                elif prediction == -1:  # SELL
                    return EnhancedSignal(symbol, "SELL", probability, current_price,
                                        current_price * 1.02, current_price * 0.98,
                                        df.index[-1].timestamp(), "ML prediction")
        
        except Exception as e:
            self.logger.error(f"ML analysis error: {e}")
        
        return EnhancedSignal(symbol, "HOLD", 0.0, current_price, 0, 0, df.index[-1].timestamp(), "ML no signal")
    
    def _combine_signals(self, tech_signal: EnhancedSignal, ml_signal: EnhancedSignal, 
                        symbol: str, current_price: float, timestamp: int) -> EnhancedSignal:
        """Combine technical and ML signals"""
        # If both agree, increase confidence
        if (tech_signal.action == ml_signal.action and 
            tech_signal.action != "HOLD" and 
            ml_signal.action != "HOLD"):
            
            combined_confidence = (tech_signal.confidence + ml_signal.confidence) / 2
            combined_reason = f"Combined: {tech_signal.reason} + {ml_signal.reason}"
            
            if tech_signal.action == "BUY":
                return EnhancedSignal(symbol, "BUY", combined_confidence, current_price,
                                    current_price * 0.98, current_price * 1.02, timestamp, combined_reason)
            else:
                return EnhancedSignal(symbol, "SELL", combined_confidence, current_price,
                                    current_price * 1.02, current_price * 0.98, timestamp, combined_reason)
        
        # If signals disagree, take the higher confidence one if it meets threshold
        if tech_signal.confidence > ml_signal.confidence and tech_signal.confidence > self.min_confidence:
            return tech_signal
        elif ml_signal.confidence > tech_signal.confidence and ml_signal.confidence > self.min_confidence:
            return ml_signal
        
        return EnhancedSignal(symbol, "HOLD", 0.0, current_price, 0, 0, timestamp, "Low confidence signals")
    
    def _load_model(self):
        """Load pre-trained ML model"""
        try:
            self.ml_model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            self.is_model_trained = True
            self.logger.info("ML model loaded successfully")
        except:
            self.logger.warning("Could not load ML model, proceeding without ML")
            self.is_model_trained = False
    
    def save_model(self):
        """Save ML model to disk"""
        if self.is_model_trained:
            joblib.dump(self.ml_model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)