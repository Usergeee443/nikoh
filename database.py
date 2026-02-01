from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


def init_db(app):
    """Initialize database"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # profiles jadvaliga phone_number ustunini qo'shish (mavjud DB uchun)
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE profiles ADD COLUMN phone_number VARCHAR(20)"
                ))
                conn.commit()
        except Exception:
            pass
        for col, typ in [
            ('aqida', 'VARCHAR(50)'),
            ('quran_reading', 'VARCHAR(50)'),
            ('mazhab', 'VARCHAR(30)'),
        ]:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE profiles ADD COLUMN {col} {typ}"))
                    conn.commit()
            except Exception:
                pass
        # Bir user bir nechta e'lon (profil) yarata olishi uchun: user_id unique olib tashlash
        for drop_stmt in [
            "ALTER TABLE profiles DROP INDEX ix_profiles_user_id",
            "ALTER TABLE profiles DROP INDEX uq_profiles_user_id",
            "ALTER TABLE profiles DROP INDEX user_id",
        ]:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(drop_stmt))
                    conn.commit()
            except Exception:
                pass
        # Bir user bir nechta e'lon (profil) yarata olishi uchun
        for col, typ in [
            ('is_primary', 'BOOLEAN DEFAULT 1'),
        ]:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE profiles ADD COLUMN {col} {typ}"))
                    conn.commit()
            except Exception:
                pass
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE match_requests ADD COLUMN receiver_profile_id INTEGER"))
                conn.commit()
        except Exception:
            pass
        for col in ['profile1_id', 'profile2_id']:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE chats ADD COLUMN {col} INTEGER"))
                    conn.commit()
            except Exception:
                pass
        # Feed tezligi uchun indekslar (mavjud DB uchun)
        for stmt in [
            "CREATE INDEX IF NOT EXISTS ix_profiles_is_active ON profiles(is_active)",
            "CREATE INDEX IF NOT EXISTS ix_profiles_gender ON profiles(gender)",
            "CREATE INDEX IF NOT EXISTS ix_profiles_activated_at ON profiles(activated_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_tariffs_is_active ON user_tariffs(is_active)",
            "CREATE INDEX IF NOT EXISTS ix_user_tariffs_is_top ON user_tariffs(is_top)",
            "CREATE INDEX IF NOT EXISTS ix_user_tariffs_expires_at ON user_tariffs(expires_at)",
            "CREATE INDEX IF NOT EXISTS ix_user_tariffs_top_expires_at ON user_tariffs(top_expires_at)",
        ]:
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(stmt))
                    conn.commit()
            except Exception:
                pass
