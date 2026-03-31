from database import db


class Setting(db.Model):
    """Key-value sozlamalar (tarif narxlari, reklama va boshqalar)"""
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=None):
        row = Setting.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = Setting.query.filter_by(key=key).first()
        if row:
            row.value = str(value) if value is not None else None
        else:
            db.session.add(Setting(key=key, value=str(value) if value is not None else None))
        db.session.commit()
