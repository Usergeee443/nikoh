from database import db
from datetime import datetime
from models.profile import Profile


class MatchRequest(db.Model):
    """MatchRequest model - tanishuv so'rovlari"""
    __tablename__ = 'match_requests'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'), nullable=True)  # qaysi e'lon (profil) uchun so'rov

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

        # Chat yaratish (qaysi profil/e'lon uchun ekanini saqlash)
        from models.user import User
        recv = User.query.get(self.receiver_id)
        sendr = User.query.get(self.sender_id)
        prof_receiver = Profile.query.get(self.receiver_profile_id) if self.receiver_profile_id else (recv.profile if recv else None)
        prof_sender = sendr.profile if sendr else None
        new_chat = Chat(
            match_request_id=self.id,
            user1_id=self.sender_id,
            user2_id=self.receiver_id,
            profile1_id=prof_sender.id if prof_sender else None,
            profile2_id=prof_receiver.id if prof_receiver else None
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
        chat_data = None
        if self.chat:
            chat_data = {
                'id': self.chat.id,
                'is_active': self.chat.is_active,
                'is_expired': self.chat.is_expired,
                'days_remaining': self.chat.days_remaining
            }
        
        # Sender ma'lumotlari
        sender_data = None
        if self.sender and self.sender.profile:
            sender_data = self.sender.profile.to_dict()
            sender_data['user_id'] = self.sender.id
            # Sender'ning aktiv tarifidagi so'rovlar soni
            if self.sender.has_active_tariff and self.sender.active_tariff:
                sender_data['requests_count'] = self.sender.active_tariff.requests_count
            else:
                sender_data['requests_count'] = 0
        
        # Receiver ma'lumotlari
        receiver_data = None
        if self.receiver and self.receiver.profile:
            receiver_data = self.receiver.profile.to_dict()
            receiver_data['user_id'] = self.receiver.id
            # Receiver'ning aktiv tarifidagi so'rovlar soni
            if self.receiver.has_active_tariff and self.receiver.active_tariff:
                receiver_data['requests_count'] = self.receiver.active_tariff.requests_count
            else:
                receiver_data['requests_count'] = 0
        
        return {
            'id': self.id,
            'sender': sender_data,
            'receiver': receiver_data,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'chat': chat_data
        }
