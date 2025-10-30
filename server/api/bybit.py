import os
import hmac
import hashlib
import requests
import json
import time
from urllib.parse import urlencode
from datetime import datetime
import logging

class BybitAPI:
    def __init__(self):
        self.api_key = os.getenv('BYBIT_API_KEY', '')
        self.api_secret = os.getenv('BYBIT_API_SECRET', '')
        self.testnet = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'
        
        if self.testnet:
            self.base_url = "https://api-testnet.bybit.com"
        else:
            self.base_url = "https://api.bybit.com"
            
        self.recv_window = "5000"
        self.logger = logging.getLogger(__name__)

    def _generate_signature(self, timestamp, method, params=None, body=None):
        """Генерация подписи для API v5 - исправленная версия"""
        # Для GET запросов - параметры в query string
        if method.upper() == 'GET' and params:
            # Сортируем параметры по ключу
            sorted_params = sorted(params.items())
            param_str = urlencode(sorted_params)
        else:
            param_str = ""
            
        # Для POST запросов - тело в формате JSON
        if method.upper() == 'POST' and body:
            # Сортируем ключи тела для консистентности
            if isinstance(body, dict):
                sorted_body = {k: body[k] for k in sorted(body.keys())}
                body_str = json.dumps(sorted_body, separators=(',', ':'))
            else:
                body_str = str(body)
        else:
            body_str = ""
            
        # Формирование строки для подписи
        signature_payload = timestamp + self.api_key + self.recv_window + param_str + body_str
        
        self.logger.debug(f"Signature payload: {signature_payload}")
        
        signature = hmac.new(
            bytes(self.api_secret, "utf-8"),
            signature_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    def _request(self, method, endpoint, params=None, body=None):
        """Универсальный метод для запросов к API v5"""
        if params is None:
            params = {}
            
        timestamp = str(int(time.time() * 1000))
        
        # Генерация подписи
        signature = self._generate_signature(timestamp, method, params, body)
        
        # Заголовки
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': self.recv_window,
            'X-BAPI-SIGN': signature,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                # Для POST запросов используем data вместо json для точного контроля
                if body:
                    # Сортируем тело для консистентности с подписью
                    if isinstance(body, dict):
                        sorted_body = {k: body[k] for k in sorted(body.keys())}
                        body_data = json.dumps(sorted_body, separators=(',', ':'))
                    else:
                        body_data = str(body)
                    response = requests.post(url, data=body_data, headers=headers, timeout=10)
                else:
                    response = requests.post(url, headers=headers, timeout=10)
            else:
                self.logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            response_data = response.json()
            
            self.logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                self.logger.error(f"API Error {response.status_code}: {response_data}")
                return None
                
            if response_data.get('retCode') != 0:
                self.logger.error(f"API Business Error [{response_data.get('retCode')}]: {response_data.get('retMsg')}")
                return None
                
            return response_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return None

    def get_account_balance(self, account_type="UNIFIED"):
        """Получение баланса счета (API v5)"""
        params = {
            'accountType': account_type
        }
        return self._request('GET', '/v5/account/wallet-balance', params=params)

    def get_positions(self, category="linear", symbol=None):
        """Получение открытых позиций (API v5)"""
        params = {
            'category': category
        }
        if symbol:
            params['symbol'] = symbol
        else:
            # Если символ не указан, получаем все позиции с settleCoin=USDT
            params['settleCoin'] = 'USDT'
            
        return self._request('GET', '/v5/position/list', params=params)

    def place_order(self, category, symbol, side, order_type, qty, price=None, time_in_force="GTC"):
        """Размещение ордера (API v5)"""
        body = {
            'category': category,
            'symbol': symbol,
            'side': side,
            'orderType': order_type,
            'qty': str(qty),  # Всегда строка
            'timeInForce': time_in_force
        }
        
        if price and order_type in ['Limit', 'Market']:
            body['price'] = str(price)  # Всегда строка
            
        return self._request('POST', '/v5/order/create', body=body)

    def get_kline(self, category, symbol, interval, limit=200):
        """Получение исторических данных (API v5)"""
        params = {
            'category': category,
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        return self._request('GET', '/v5/market/kline', params=params)

    def get_server_time(self):
        """Получение времени сервера Bybit"""
        return self._request('GET', '/v5/market/time')