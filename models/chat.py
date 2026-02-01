from database import db
from datetime import datetime, timedelta
from config import Config


class Chat(db.Model):
    """Chat model - 7 kunlik chatlar"""
    __tablename__ = 'chats'

    id = db.Column(db.Integer, primary_key=True)
    match_request_id = db.Column(db.Integer, db.ForeignKey('match_requests.id'), nullable=False)
    user1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    profile1_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=True)  # user1 qaysi e'lon (profil) uchun
    profile2_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=True)  # user2 qaysi e'lon uchun

    # Chat muddati
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Messages relationship
    messages = db.relationship('Message', backref='chat', lazy='dynamic',
                              order_by='Message.created_at', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(Chat, self).__init__(**kwargs)
        # Chat ochilganda 7 kun muddatini o'rnatish
        self.expires_at = datetime.utcnow() + timedelta(days=Config.CHAT_DURATION_DAYS)

    def __repr__(self):
        return f'<Chat {self.id}>'

    @property
    def is_expired(self):
        """Chat muddati tugaganmi?"""
        return datetime.utcnow() > self.expires_at

    @property
    def days_remaining(self):
        """Qolgan kunlar soni"""
        if self.is_expired:
            return 0
        remaining = self.expires_at - datetime.utcnow()
        return max(0, remaining.days)

    @property
    def hours_remaining(self):
        """Qolgan soatlar soni"""
        if self.is_expired:
            return 0
        remaining = self.expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds() / 3600))

    def check_and_update_status(self):
        """Holatni tekshirish va yangilash"""
        if self.is_expired and self.is_active:
            self.is_active = False
            db.session.commit()

    def get_other_user_id(self, current_user_id):
        """Boshqa foydalanuvchi ID sini olish"""
        if current_user_id == self.user1_id:
            return self.user2_id
        return self.user1_id

    def get_messages(self, limit=100):
        """Chatning xabarlarini olish"""
        return self.messages.order_by(Message.created_at.asc()).limit(limit).all()

    def get_my_profile_id(self, current_user_id):
        """Joriy foydalanuvchining ushbu chatdagi profil id si"""
        if current_user_id == self.user1_id:
            return self.profile1_id
        return self.profile2_id

    def to_dict(self, current_user_id=None):
        """Chatni dictionary ga aylantirish"""
        other_user_id = self.get_other_user_id(current_user_id) if current_user_id else None
        other_user = None

        if other_user_id:
            from models.user import User
            other_user = User.query.get(other_user_id)

        my_profile_id = self.get_my_profile_id(current_user_id) if current_user_id else None
        return {
            'id': self.id,
            'other_user': other_user.profile.to_dict() if other_user and other_user.profile else None,
            'profile_id': my_profile_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_expired': self.is_expired,
            'days_remaining': self.days_remaining,
            'hours_remaining': self.hours_remaining
        }


class Message(db.Model):
    """Message model - chat xabarlari"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Xabar ma'lumotlari
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)

    # Vaqt
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Sender relationship
    sender = db.relationship('User', backref='messages')

    def __repr__(self):
        return f'<Message {self.id}>'

    def to_dict(self):
        """Xabarni dictionary ga aylantirish"""
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def mark_as_read(self):
        """Xabarni o'qilgan deb belgilash"""
        self.is_read = True
        db.session.commit()
