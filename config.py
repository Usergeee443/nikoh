import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///nikoh.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Telegram Bot settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL')

    # Mini App settings
    MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://your-app.com')

    # Admin settings
    ADMIN_TELEGRAM_IDS = os.getenv('ADMIN_TELEGRAM_IDS', '').split(',')

    # Tariff settings
    KUMUSH_TARIFF_REQUESTS = 5  # 5 ta so'rov
    KUMUSH_TARIFF_DAYS = 10  # 10 kun e'lon
    KUMUSH_TARIFF_TOP_DAYS = 3  # 3 kun TOP
    KUMUSH_TARIFF_PRICE = 50000  # 50,000 so'm

    # Chat settings
    CHAT_DURATION_DAYS = 7  # 7 kunlik chat

    # Payment card info
    PAYMENT_CARD_NUMBER = os.getenv('PAYMENT_CARD_NUMBER', '8600 1234 5678 9012')
    PAYMENT_CARD_NAME = os.getenv('PAYMENT_CARD_NAME', 'NIKOH APP')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
