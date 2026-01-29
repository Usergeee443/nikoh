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
            print("🤖 Telegram bot polling boshlandi...")
            telegram_app.run_polling(stop_signals=None, drop_pending_updates=True)
        except Exception as e:
            print(f"❌ Bot xatosi: {e}")
            import traceback
            traceback.print_exc()


# Production rejimida (Gunicorn) botni avtomatik ishga tushirish
# Gunicorn ishlatilganda `if __name__ == '__main__'` bloki ishlamaydi,
# shuning uchun botni bu yerda ishga tushirish kerak
if telegram_app and (env == 'production' or os.getenv('GUNICORN_CMD_ARGS')):
    # Faqat bir marta ishga tushirish uchun
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Telegram bot production rejimida ishga tushdi!")


@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'app': 'NIKOH'}


if __name__ == '__main__':
    # Development rejimida botni ishga tushirish
    # Botni faqat reloader subprocess'da ishga tushirish (WERKZEUG_RUN_MAIN mavjud bo'lganda)
    if telegram_app and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        print("✅ Telegram bot development rejimida ishga tushdi!")
    
    # Development rejimida ishlatish
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)