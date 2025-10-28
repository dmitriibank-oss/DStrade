import requests
import pandas as pd
import time
import hmac
import hashlib
import json
from config.config import Config
from src.logger import TradingLogger

class BybitClient:
    def __init__(self):
        self.logger = TradingLogger()
        self.testnet = Config.TESTNET
        self.base_url = "https://api-testnet.bybit.com" if self.testnet else "https://api.bybit.com"
        self.api_key = Config.BYBIT_API_KEY
        self.api_secret = Config.BYBIT_API_SECRET
        
        # Проверяем наличие API ключей
        if not self.api_key or not self.api_secret:
            self.logger.log("ERROR: API keys not found in .env file", 'error')
            raise ValueError("API keys not configured")
        
        self.logger.log("Bybit client initialized successfully", 'info')
    
    def _generate_signature(self, timestamp, recv_window, params=None, method="GET"):
        """Генерация подписи для API запросов v5"""
        try:
            if method.upper() == "GET" and params:
                # Для GET: параметры как query string
                param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
                sign_str = timestamp + self.api_key + recv_window + param_str
            else:
                # Для POST: параметры как JSON строка
                param_str = json.dumps(params) if params else "{}"
                sign_str = timestamp + self.api_key + recv_window + param_str
            
            signature = hmac.new(
                bytes(self.api_secret, "utf-8"),
                bytes(sign_str, "utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            return signature
            
        except Exception as e:
            self.logger.log(f"Error generating signature: {e}", 'error')
            return None
    
    def _make_request(self, method, endpoint, params=None):
        """Выполнение API запроса для v5"""
        try:
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"
            
            # Генерируем подпись
            signature = self._generate_signature(timestamp, recv_window, params, method)
            if not signature:
                return None
            
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window,
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            else:
                headers["Content-Type"] = "application/json"
                response = requests.post(url, headers=headers, json=params, timeout=10)
            
            # Детальная диагностика ответа
            self.logger.log(f"Response status: {response.status_code}", 'info')
            
            if response.status_code != 200:
                self.logger.log(f"API error: Status {response.status_code}, Response: {response.text}", 'error')
                return None
                
            result = response.json()
            
            # Проверяем код возврата Bybit
            ret_code = result.get('retCode')
            ret_msg = result.get('retMsg', 'No message')
            
            if ret_code != 0:
                self.logger.log(f"Bybit API error {ret_code}: {ret_msg}", 'error')
                return None
                
            self.logger.log(f"API request successful: {ret_msg}", 'info')
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.log(f"Network error: {e}", 'error')
            return None
        except json.JSONDecodeError as e:
            self.logger.log(f"JSON decode error: {e}", 'error')
            return None
        except Exception as e:
            self.logger.log(f"API request error: {e}", 'error')
            return None
    
    def test_connection(self):
        """Тест подключения к API"""
        self.logger.log("Testing API connection...", 'info')
        
        # Простой запрос для проверки подключения
        response = self._make_request('GET', '/v5/market/time')
        
        if response and 'result' in response:
            server_time = response['result'].get('timeSecond', 'Unknown')
            self.logger.log(f"API connection successful. Server time: {server_time}", 'info')
            return True
        else:
            self.logger.log("API connection failed", 'error')
            return False
    
    def get_account_balance(self):
        """Получение баланса аккаунта через API v5 - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        self.logger.log("Getting account balance...", 'info')
        
        try:
            response = self._make_request('GET', '/v5/account/wallet-balance', {
                'accountType': 'UNIFIED'
            })
            
            if response and 'result' in response:
                balance_list = response['result'].get('list', [])
                if balance_list and len(balance_list) > 0:
                    # Ищем USDT баланс
                    for coin in balance_list[0].get('coin', []):
                        if coin.get('coin') == 'USDT':
                            # Пробуем разные поля баланса в порядке приоритета
                            balance = coin.get('availableToWithdraw')
                            if balance is None or balance == '':
                                balance = coin.get('availableBalance')
                            if balance is None or balance == '':
                                balance = coin.get('walletBalance')
                            
                            # Проверяем, что баланс не пустой и может быть сконвертирован
                            if balance and balance != '':
                                try:
                                    balance_float = float(balance)
                                    self.logger.log(f"Account balance: {balance_float} USDT", 'info')
                                    return balance_float
                                except (ValueError, TypeError) as e:
                                    self.logger.log(f"Error converting balance '{balance}' to float: {e}", 'error')
                                    continue
            
            self.logger.log("Could not retrieve balance from API, using initial balance", 'warning')
            return Config.INITIAL_BALANCE
            
        except Exception as e:
            self.logger.log(f"Error getting balance: {e}", 'error')
            return Config.INITIAL_BALANCE
    
    def get_current_price(self, symbol):
        """Получение текущей цены через API v5"""
        try:
            response = self._make_request('GET', '/v5/market/tickers', {
                'category': 'linear',
                'symbol': symbol
            })
            
            if response and 'result' in response and 'list' in response['result']:
                tickers = response['result']['list']
                if tickers and len(tickers) > 0:
                    price = float(tickers[0]['lastPrice'])
                    return price
            
            self.logger.log(f"Could not get price for {symbol}", 'warning')
            return None
            
        except Exception as e:
            self.logger.log(f"Error getting price for {symbol}: {e}", 'error')
            return None
    
    def get_klines(self, symbol, interval='15', limit=100):
        """Получение исторических данных через API v5"""
        try:
            response = self._make_request('GET', '/v5/market/kline', {
                'category': 'linear',
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            })
            
            if response and 'result' in response and 'list' in response['result']:
                klines = response['result']['list']
                if not klines:
                    self.logger.log(f"No kline data for {symbol}", 'warning')
                    return None
                
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
                ])
                
                # Конвертация типов данных
                df['open'] = pd.to_numeric(df['open'], errors='coerce')
                df['high'] = pd.to_numeric(df['high'], errors='coerce')
                df['low'] = pd.to_numeric(df['low'], errors='coerce')
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                
                # Удаление строк с NaN
                df = df.dropna()
                
                if len(df) < 20:
                    self.logger.log(f"Not enough data for {symbol}: {len(df)} rows", 'warning')
                    return None
                
                self.logger.log(f"Retrieved {len(df)} klines for {symbol}", 'info')
                return df
            
            return None
            
        except Exception as e:
            self.logger.log(f"Error getting klines for {symbol}: {e}", 'error')
            return None
    
    def place_order(self, symbol, side, quantity, order_type="Market"):
        """Размещение ордера через API v5 - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            # Рассчитываем размер позиции
            qty = str(round(quantity, 4))
            
            # Исправляем сторону ордера для Bybit API v5
            # Bybit ожидает "Buy" или "Sell" (с заглавной буквы)
            bybit_side = "Buy" if side.upper() == "BUY" else "Sell"
            
            params = {
                'category': 'linear',
                'symbol': symbol,
                'side': bybit_side,  # Используем исправленную сторону
                'orderType': order_type,
                'qty': qty,
                'timeInForce': 'GTC',
                'positionIdx': 0  # Добавляем обязательный параметр для хеджирования
            }
            
            self.logger.log(f"Placing order: {bybit_side} {qty} {symbol}", 'info')
            
            response = self._make_request('POST', '/v5/order/create', params)
            
            if response and 'result' in response:
                order_id = response['result'].get('orderId', 'Unknown')
                self.logger.log(f"Order placed successfully: {bybit_side} {qty} {symbol} (ID: {order_id})", 'info', True)
                return response
            else:
                self.logger.log(f"Order failed for {symbol}", 'error', True)
                return None
                
        except Exception as e:
            self.logger.log(f"Error placing order for {symbol}: {e}", 'error', True)
            return None
    
    def get_server_time(self):
        """Получение времени сервера для тестирования подключения"""
        try:
            response = self._make_request('GET', '/v5/market/time', {})
            if response and 'result' in response:
                return response['result']['timeSecond']
            return None
        except Exception as e:
            self.logger.log(f"Error getting server time: {e}", 'error')
            return None