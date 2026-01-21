from database import db
from datetime import datetime


class User(db.Model):
    """User model - asosiy foydalanuvchi ma'lumotlari"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False, index=True)
    username = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')
    tariffs = db.relationship('UserTariff', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_requests = db.relationship('MatchRequest', foreign_keys='MatchRequest.sender_id',
                                   backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    received_requests = db.relationship('MatchRequest', foreign_keys='MatchRequest.receiver_id',
                                       backref='receiver', lazy='dynamic', cascade='all, delete-orphan')
    chats_as_user1 = db.relationship('Chat', foreign_keys='Chat.user1_id',
                                     backref='user1', lazy='dynamic', cascade='all, delete-orphan')
    chats_as_user2 = db.relationship('Chat', foreign_keys='Chat.user2_id',
                                     backref='user2', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.telegram_id}>'

    @property
    def has_active_tariff(self):
        """Foydalanuvchining aktiv tarifi bormi?"""
        from models.tariff import UserTariff
        active_tariff = self.tariffs.filter(
            UserTariff.is_active == True,
            UserTariff.expires_at > datetime.utcnow()
        ).first()
        return active_tariff is not None

    @property
    def active_tariff(self):
        """Aktiv tarifni qaytaradi"""
        from models.tariff import UserTariff
        return self.tariffs.filter(
            UserTariff.is_active == True,
            UserTariff.expires_at > datetime.utcnow()
        ).first()

    @property
    def profile_completed(self):
        """Profil to'liqmi?"""
        if not self.profile:
            return False
        return self.profile.is_complete

    def get_chats(self):
        """Foydalanuvchining barcha chatlarini olish"""
        from models.chat import Chat
        return Chat.query.filter(
            db.or_(Chat.user1_id == self.id, Chat.user2_id == self.id)
        ).order_by(Chat.created_at.desc()).all()
