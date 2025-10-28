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
        
        if not self.api_key or not self.api_secret:
            self.logger.log("ERROR: API keys not found in .env file", 'error')
            raise ValueError("API keys not configured")
        
        self.logger.log("Bybit client initialized successfully", 'info')
    
    def _generate_signature(self, timestamp, recv_window, params=None, method="GET"):
        """Генерация подписи для API запросов v5"""
        try:
            if method.upper() == "GET" and params:
                param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
                sign_str = timestamp + self.api_key + recv_window + param_str
            else:
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
            
            if response.status_code != 200:
                self.logger.log(f"API error: Status {response.status_code}, Response: {response.text}", 'error')
                return None
                
            result = response.json()
            
            ret_code = result.get('retCode')
            ret_msg = result.get('retMsg', 'No message')
            
            if ret_code != 0:
                self.logger.log(f"Bybit API error {ret_code}: {ret_msg}", 'error')
                return None
                
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
        
        response = self._make_request('GET', '/v5/market/time')
        
        if response and 'result' in response:
            server_time = response['result'].get('timeSecond', 'Unknown')
            self.logger.log(f"API connection successful. Server time: {server_time}", 'info')
            return True
        else:
            self.logger.log("API connection failed", 'error')
            return False
    
    def get_account_balance(self):
        """Получение баланса аккаунта"""
        self.logger.log("Getting account balance...", 'info')
        
        try:
            response = self._make_request('GET', '/v5/account/wallet-balance', {
                'accountType': 'UNIFIED'
            })
            
            if response and 'result' in response:
                balance_list = response['result'].get('list', [])
                if balance_list and len(balance_list) > 0:
                    for coin in balance_list[0].get('coin', []):
                        if coin.get('coin') == 'USDT':
                            balance = coin.get('availableToWithdraw')
                            if balance is None or balance == '':
                                balance = coin.get('availableBalance')
                            if balance is None or balance == '':
                                balance = coin.get('walletBalance')
                            
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
        """Получение текущей цены"""
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
        """Получение исторических данных"""
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
                
                df['open'] = pd.to_numeric(df['open'], errors='coerce')
                df['high'] = pd.to_numeric(df['high'], errors='coerce')
                df['low'] = pd.to_numeric(df['low'], errors='coerce')
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                
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
    
    def place_order(self, symbol, side, quantity, order_type="Market", price=None):
        """Размещение ордера с улучшенной обработкой"""
        try:
            qty = str(round(quantity, 4))
            bybit_side = "Buy" if side.upper() == "BUY" else "Sell"
            
            params = {
                'category': 'linear',
                'symbol': symbol,
                'side': bybit_side,
                'orderType': order_type,
                'qty': qty,
                'timeInForce': 'GTC',
                'positionIdx': 0
            }
            
            # Добавляем цену для лимитных ордеров
            if order_type == "Limit" and price is not None:
                params['price'] = str(round(price, 4))
            
            self.logger.log(f"Placing order: {bybit_side} {qty} {symbol} ({order_type})", 'info')
            
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
    
    def get_open_positions(self):
        """Получение открытых позиций с исправленной обработкой"""
        try:
            response = self._make_request('GET', '/v5/position/list', {
                'category': 'linear',
                'settleCoin': 'USDT'
            })
            
            if response and 'result' in response and 'list' in response['result']:
                positions = response['result']['list']
                active_positions = []
                
                for pos in positions:
                    try:
                        # Безопасное преобразование размеров
                        size_str = pos.get('size', '0')
                        size = float(size_str) if size_str and size_str != '' else 0.0
                        
                        if size > 0:
                            # Безопасное преобразование цен
                            avg_price_str = pos.get('avgPrice', '0')
                            avg_price = float(avg_price_str) if avg_price_str and avg_price_str != '' else 0.0
                            
                            leverage_str = pos.get('leverage', '1')
                            leverage = float(leverage_str) if leverage_str and leverage_str != '' else 1.0
                            
                            liq_price_str = pos.get('liqPrice', '0')
                            liq_price = float(liq_price_str) if liq_price_str and liq_price_str != '' else 0.0
                            
                            unrealised_pnl_str = pos.get('unrealisedPnl', '0')
                            unrealised_pnl = float(unrealised_pnl_str) if unrealised_pnl_str and unrealised_pnl_str != '' else 0.0
                            
                            active_positions.append({
                                'symbol': pos['symbol'],
                                'side': pos['side'],
                                'size': size,
                                'entry_price': avg_price,
                                'leverage': leverage,
                                'liq_price': liq_price,
                                'unrealised_pnl': unrealised_pnl
                            })
                    except (ValueError, TypeError) as e:
                        self.logger.log(f"Error parsing position data for {pos.get('symbol', 'unknown')}: {e}", 'warning')
                        continue
                
                return active_positions
            
            return []
            
        except Exception as e:
            self.logger.log(f"Error getting positions: {e}", 'error')
            return []