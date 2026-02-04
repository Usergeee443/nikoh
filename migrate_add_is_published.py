#!/usr/bin/env python3
"""
Migration skripti: Profile jadvaliga is_published ustunini qo'shish
MySQL va SQLite uchun universal
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def migrate():
    try:
        from app import app
        from database import db
        
        with app.app_context():
            # Check if column exists using raw SQL
            try:
                result = db.session.execute(db.text("SHOW COLUMNS FROM profiles LIKE 'is_published'"))
                exists = result.fetchone() is not None
            except:
                # SQLite fallback
                try:
                    result = db.session.execute(db.text("PRAGMA table_info(profiles)"))
                    columns = [row[1] for row in result.fetchall()]
                    exists = 'is_published' in columns
                except:
                    exists = False
            
            if exists:
                print("✅ is_published ustuni allaqachon mavjud")
            else:
                print("📝 is_published ustuni qo'shilmoqda...")
                try:
                    # MySQL syntax
                    db.session.execute(db.text("ALTER TABLE profiles ADD COLUMN is_published BOOLEAN DEFAULT TRUE"))
                except:
                    # SQLite syntax
                    db.session.execute(db.text("ALTER TABLE profiles ADD COLUMN is_published INTEGER DEFAULT 1"))
                
                db.session.commit()
                print("✅ is_published ustuni muvaffaqiyatli qo'shildi")
            
            # Update existing rows
            db.session.execute(db.text("UPDATE profiles SET is_published = 1 WHERE is_published IS NULL"))
            db.session.commit()
            print("✅ Mavjud e'lonlar yangilandi")
            
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        return False
    
    return True

if __name__ == '__main__':
    migrate()
