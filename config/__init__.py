# config/__init__.py
from .config import Config

class DevelopmentConfig(Config):
    TESTNET = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    TESTNET = False  
    LOG_LEVEL = 'INFO'