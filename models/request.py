from database import db
from datetime import datetime


class MatchRequest(db.Model):
    """MatchRequest model - tanishuv so'rovlari"""
    __tablename__ = 'match_requests'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # So'rov ma'lumotlari
    message = db.Column(db.Text)  # Qo'shimcha xabar (ixtiyoriy)
    status = db.Column(db.String(20), default='pending')  # pending / accepted / rejected / cancelled

    # Vaqtlar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

    # Chat relationship
    chat = db.relationship('Chat', backref='match_request', uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<MatchRequest {self.id} - {self.status}>'

    @property
    def is_pending(self):
        """So'rov kutilayaptimi?"""
        return self.status == 'pending'

    @property
    def is_accepted(self):
        """So'rov qabul qilinganmi?"""
        return self.status == 'accepted'

    @property
    def is_rejected(self):
        """So'rov rad etilganmi?"""
        return self.status == 'rejected'

    @property
    def is_cancelled(self):
        """So'rov bekor qilinganmi?"""
        return self.status == 'cancelled'

    def accept(self):
        """So'rovni qabul qilish"""
        from models.chat import Chat

        self.status = 'accepted'
        self.responded_at = datetime.utcnow()

        # Chat yaratish
        new_chat = Chat(
            match_request_id=self.id,
            user1_id=self.sender_id,
            user2_id=self.receiver_id
        )
        db.session.add(new_chat)
        db.session.commit()

        return new_chat

    def reject(self):
        """So'rovni rad etish"""
        self.status = 'rejected'
        self.responded_at = datetime.utcnow()
        db.session.commit()

    def cancel(self):
        """So'rovni bekor qilish"""
        if self.is_pending:
            self.status = 'cancelled'
            self.responded_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    def to_dict(self):
        """So'rovni dictionary ga aylantirish"""
        return {
            'id': self.id,
            'sender': self.sender.profile.to_dict() if self.sender.profile else None,
            'receiver': self.receiver.profile.to_dict() if self.receiver.profile else None,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None
        }
