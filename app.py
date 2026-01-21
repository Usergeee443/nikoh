from flask import Flask
from config import config
from database import init_db
from routes import register_blueprints
from telegram_bot import setup_bot, set_flask_app
import os

# Flask ilovasini yaratish
app = Flask(__name__)

# Konfiguratsiya
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Session uchun secret key
app.secret_key = app.config['SECRET_KEY']

# Database'ni sozlash
init_db(app)

# Blueprintlarni ro'yxatdan o'tkazish
register_blueprints(app)

# Telegram botni sozlash
set_flask_app(app)
telegram_app = setup_bot(app)


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'app': 'NIKOH'}


if __name__ == '__main__':
    # Development rejimida ishlatish
    app.run(debug=True, host='0.0.0.0', port=5000)