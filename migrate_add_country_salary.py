#!/usr/bin/env python3
"""Profiles jadvaliga country va salary ustunlarini qo'shish (agar bo'lmasa)."""
import os
import sys

# Loyiha ildizini path ga qo'shish
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        from sqlalchemy import inspect
        insp = inspect(db.engine)
        cols = [c['name'] for c in insp.get_columns('profiles')]
        for col in ['country', 'salary']:
            if col not in cols:
                print(f"Qo'shilmoqda: {col}")
                db.session.execute(text(f'ALTER TABLE profiles ADD COLUMN {col} VARCHAR(100)'))
                db.session.commit()
                print(f"  {col} qo'shildi.")
            else:
                print(f"  {col} allaqachon mavjud.")
    print("Migratsiya tugadi.")

if __name__ == '__main__':
    migrate()
