import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    # MySQL DSN (mysql+pymysql) - DATABASE_URL orqali beriladi, default sifatida lokal MySQL misoli
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://user:password@localhost:3306/nikoh')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Ulanish pool: eski/uzilgan ulanishlardan qochish (Lost connection / Operation timed out)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # ulanishdan oldin tekshirish, uzilgan bo'lsa yangisini olish
        "pool_recycle": 280,    # 280 sekunddan keyin ulanishni yangilash (MySQL wait_timeout dan oldin)
    }

    # Telegram Bot settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL')
    TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME', 'nikoh_bot')

    # Mini App settings
    MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://your-app.com')

    # Admin settings
    ADMIN_TELEGRAM_IDS = os.getenv('ADMIN_TELEGRAM_IDS', '').split(',')

    # Tariff settings - KUMUSH (Silver)
    KUMUSH_TARIFF_REQUESTS = 5  # 5 ta so'rov
    KUMUSH_TARIFF_DAYS = 10  # 10 kun e'lon
    KUMUSH_TARIFF_TOP_DAYS = 0  # TOP yo'q
    KUMUSH_TARIFF_PRICE = 50000  # 50,000 so'm
    
    # Tariff settings - OLTIN (Gold)
    OLTIN_TARIFF_REQUESTS = 10  # 10 ta so'rov
    OLTIN_TARIFF_DAYS = 15  # 15 kun e'lon
    OLTIN_TARIFF_TOP_DAYS = 7  # 7 kun TOP
    OLTIN_TARIFF_PRICE = 100000  # 100,000 so'm
    
    # Tariff settings - VIP
    VIP_TARIFF_REQUESTS = 20  # 20 ta so'rov
    VIP_TARIFF_DAYS = 30  # 30 kun e'lon
    VIP_TARIFF_TOP_DAYS = 15  # 15 kun TOP
    VIP_TARIFF_PRICE = 250000  # 250,000 so'm

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
