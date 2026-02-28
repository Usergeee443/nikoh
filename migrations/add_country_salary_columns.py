"""
Migration script to add 'country' and 'salary' columns to the Profile table.

Run this script after deploying the new code:
    python migrations/add_country_salary_columns.py

This is a one-time migration that should be run when the new columns are needed.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db
from sqlalchemy import text, inspect


def migrate():
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('profile')]

        print(f"Current columns in 'profile' table: {columns}")

        # Add 'country' column if it doesn't exist
        if 'country' not in columns:
            print("Adding 'country' column...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE profile ADD COLUMN country VARCHAR(100)'))
                conn.commit()
            print("  'country' column added successfully!")
        else:
            print("  'country' column already exists, skipping.")

        # Add 'salary' column if it doesn't exist
        if 'salary' not in columns:
            print("Adding 'salary' column...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE profile ADD COLUMN salary VARCHAR(50)'))
                conn.commit()
            print("  'salary' column added successfully!")
        else:
            print("  'salary' column already exists, skipping.")

        print("\nMigration completed successfully!")


if __name__ == '__main__':
    migrate()
