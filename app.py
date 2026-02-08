from flask import Flask
from flask_compress import Compress
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

# Gzip/Brotli siqish — JSON va HTML uchun tarmoq hajmini kamaytiradi
Compress(app)

# Session uchun secret key
app.secret_key = app.config['SECRET_KEY']

# Database'ni sozlash
init_db(app)

# Migratsiya: is_published ustunini qo'shish va user_id UNIQUE cheklovini olib tashlash
def run_migrations():
    from database import db
    with app.app_context():
        # 0. partner_country ustunini qo'shish (juftga talablari uchun)
        try:
            result = db.session.execute(db.text("SHOW COLUMNS FROM profiles LIKE 'partner_country'"))
            if not result.fetchone():
                print("📝 partner_country ustuni qo'shilmoqda...")
                db.session.execute(db.text("ALTER TABLE profiles ADD COLUMN partner_country VARCHAR(100)"))
                db.session.commit()
                print("✅ partner_country ustuni qo'shildi")
        except Exception as e:
            db.session.rollback()
            if 'Duplicate' not in str(e) and 'already exists' not in str(e).lower():
                print(f"⚠️ Migratsiya (partner_country): {e}")
        # 0.2 smoking, sport_days (jismoniy)
        try:
            for col, typ in [('smoking', 'VARCHAR(20)'), ('sport_days', 'INT')]:
                result = db.session.execute(db.text(f"SHOW COLUMNS FROM profiles LIKE '{col}'"))
                if not result.fetchone():
                    db.session.execute(db.text(f"ALTER TABLE profiles ADD COLUMN {col} {typ}"))
                    db.session.commit()
                    print(f"✅ {col} ustuni qo'shildi")
        except Exception as e:
            db.session.rollback()
            if 'Duplicate' not in str(e) and 'already exists' not in str(e).lower():
                print(f"⚠️ Migratsiya (smoking/sport_days): {e}")
        # 0.1 partner_locations (JSON, ko'p joy tanlash)
        try:
            result = db.session.execute(db.text("SHOW COLUMNS FROM profiles LIKE 'partner_locations'"))
            if not result.fetchone():
                print("📝 partner_locations ustuni qo'shilmoqda...")
                db.session.execute(db.text("ALTER TABLE profiles ADD COLUMN partner_locations TEXT"))
                db.session.commit()
                print("✅ partner_locations ustuni qo'shildi")
        except Exception as e:
            db.session.rollback()
            if 'Duplicate' not in str(e) and 'already exists' not in str(e).lower():
                print(f"⚠️ Migratsiya (partner_locations): {e}")
        # 1. is_published ustunini qo'shish
        try:
            result = db.session.execute(db.text("SHOW COLUMNS FROM profiles LIKE 'is_published'"))
            if not result.fetchone():
                print("📝 is_published ustuni qo'shilmoqda...")
                db.session.execute(db.text("ALTER TABLE profiles ADD COLUMN is_published BOOLEAN DEFAULT TRUE"))
                db.session.execute(db.text("UPDATE profiles SET is_published = 1 WHERE is_published IS NULL"))
                db.session.commit()
                print("✅ is_published ustuni qo'shildi")
        except Exception as e:
            db.session.rollback()
            if 'Duplicate' not in str(e) and 'already exists' not in str(e).lower():
                print(f"⚠️ Migratsiya (is_published): {e}")
        
        # 2. user_id UNIQUE cheklovini olib tashlash (bir user ko'p e'lon yarata olishi uchun)
        try:
            # MySQL: user_id ustunidagi UNIQUE indeks FK bilan bog'liq bo'lishi mumkin — avval FK ni olib tashlash kerak
            dialect = db.engine.url.get_dialect().name
            if dialect == 'mysql':
                # FK nomini topish (user_id orqali users ga bog'langan)
                r = db.session.execute(db.text("""
                    SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'profiles'
                    AND COLUMN_NAME = 'user_id' AND REFERENCED_TABLE_NAME IS NOT NULL
                    LIMIT 1
                """))
                fk_row = r.fetchone()
                fk_name = fk_row[0] if fk_row else None
                # user_id ustunida UNIQUE indeks bormi (information_schema orqali)
                r2 = db.session.execute(db.text("""
                    SELECT INDEX_NAME FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'profiles'
                    AND COLUMN_NAME = 'user_id' AND NON_UNIQUE = 0 LIMIT 1
                """))
                uq_row = r2.fetchone()
                if uq_row and fk_name:
                    idx_name = uq_row[0]
                    print("📝 MySQL: user_id UNIQUE olib tashlanmoqda (FK vaqtincha o'chiriladi)...")
                    db.session.execute(db.text(f"ALTER TABLE profiles DROP FOREIGN KEY `{fk_name}`"))
                    db.session.execute(db.text(f"ALTER TABLE profiles DROP INDEX `{idx_name}`"))
                    db.session.execute(db.text(f"ALTER TABLE profiles ADD CONSTRAINT `{fk_name}` FOREIGN KEY (user_id) REFERENCES users(id)"))
                    db.session.commit()
                    print("✅ user_id UNIQUE olib tashlandi, FK qayta qo'shildi")
                elif fk_name is None:
                    # UNIQUE boshqa indeks nomida bo'lishi mumkin
                    r3 = db.session.execute(db.text("SHOW INDEX FROM profiles WHERE Column_name = 'user_id'"))
                    for row in r3.fetchall():
                        idx_name = row[2]
                        if idx_name != 'PRIMARY':
                            db.session.execute(db.text(f"ALTER TABLE profiles DROP INDEX `{idx_name}`"))
                            db.session.commit()
                            print(f"✅ {idx_name} indeksi o'chirildi")
                            break
            else:
                # SQLite: SHOW INDEX yo'q; database.py dagi DROP INDEX urinishlari yetarli
                pass
        except Exception as e:
            db.session.rollback()
            if "Can't DROP" not in str(e) and "check that" not in str(e).lower() and "Duplicate" not in str(e):
                print(f"⚠️ Migratsiya (user_id unique): {e}")

        # 3. is_published=True bo'lgan qo'shimcha e'lonlarni is_active=True qilish
        try:
            updated = db.session.execute(db.text(
                "UPDATE profiles SET is_active = 1, activated_at = NOW() "
                "WHERE is_published = 1 AND (is_active = 0 OR is_active IS NULL)"
            ))
            if updated.rowcount > 0:
                db.session.commit()
                print(f"✅ {updated.rowcount} ta e'lon is_active=True qilindi")
            else:
                db.session.rollback()
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Migratsiya (is_active sync): {e}")

run_migrations()

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