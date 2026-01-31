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
            pass  # Ustun allaqachon mavjud
