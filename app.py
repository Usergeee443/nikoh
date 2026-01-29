from flask import Flask
from config import config
from database import init_db
from routes import register_blueprints
from telegram_bot import setup_bot, set_flask_app
import os
import threading
import asyncio

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

# Telegram botni sozlash (ixtiyoriy - agar token bo'lmasa, bot ishlamaydi)
telegram_app = None
try:
    set_flask_app(app)
    telegram_app = setup_bot(app)
    if telegram_app:
        print("✅ Telegram bot sozlandi!")
    else:
        print("⚠️ Telegram bot token topilmadi. Bot ishlamaydi.")
except Exception as e:
    print(f"⚠️ Telegram bot sozlashda xatolik: {e}")
    print("⚠️ Bot ishlamaydi, lekin web ilova ishlaydi.")


def run_bot():
    """Botni alohida threadda ishga tushirish"""
    if telegram_app:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Signal handler'larni o'chirish uchun stop_signals=None
            telegram_app.run_polling(stop_signals=None)
        except Exception as e:
            print(f"❌ Bot xatosi: {e}")


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'app': 'NIKOH'}


if __name__ == '__main__':
    # Botni faqat reloader subprocess'da ishga tushirish (WERKZEUG_RUN_MAIN mavjud bo'lganda)
    # Bu botni faqat bir marta ishga tushirishni ta'minlaydi
    # Werkzeug reloader asosiy process'da botni ishga tushirmaydi, faqat subprocess'da
    if telegram_app and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        print("✅ Telegram bot ishga tushdi!")
    
    # Development rejimida ishlatish
    # use_reloader=True - reloader yoqilgan, lekin bot faqat subprocess'da ishga tushadi
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)