from database import db
from datetime import datetime, timedelta


class UserTariff(db.Model):
    """UserTariff model - foydalanuvchi tariflari"""
    __tablename__ = 'user_tariffs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Tarif ma'lumotlari
    tariff_name = db.Column(db.String(50), default='KUMUSH')  # Hozircha faqat KUMUSH
    requests_count = db.Column(db.Integer, default=5)  # Qolgan so'rovlar soni
    total_requests = db.Column(db.Integer, default=5)  # Jami so'rovlar soni

    # Muddatlar
    duration_days = db.Column(db.Integer, default=10)  # E'lon muddati
    top_duration_days = db.Column(db.Integer, default=3)  # TOP da turish muddati

    # Holatlar
    is_active = db.Column(db.Boolean, default=False, index=True)
    is_top = db.Column(db.Boolean, default=True, index=True)  # TOP da ko'rsatish

    # Vaqtlar
    activated_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime, index=True)
    top_expires_at = db.Column(db.DateTime, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Payment request relationship
    payment_request_id = db.Column(db.Integer, db.ForeignKey('payment_requests.id'))

    def __repr__(self):
        return f'<UserTariff {self.tariff_name} - User {self.user_id}>'

    def activate(self):
        """Tarifni faollashtirish"""
        self.is_active = True
        self.activated_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=self.duration_days)
        self.top_expires_at = datetime.utcnow() + timedelta(days=self.top_duration_days)
        db.session.commit()

    def use_request(self):
        """So'rov ishlatish"""
        if self.requests_count > 0:
            self.requests_count -= 1
            db.session.commit()
            return True
        return False

    @property
    def is_expired(self):
        """Tarif muddati tugaganmi?"""
        if not self.expires_at:
            return True
        return datetime.utcnow() > self.expires_at

    @property
    def is_top_expired(self):
        """TOP muddati tugaganmi?"""
        if not self.top_expires_at:
            return True
        return datetime.utcnow() > self.top_expires_at

    @property
    def days_remaining(self):
        """Qolgan kunlar soni"""
        if not self.expires_at:
            return 0
        remaining = self.expires_at - datetime.utcnow()
        return max(0, remaining.days)

    @property
    def top_days_remaining(self):
        """TOP qolgan kunlar soni"""
        if not self.top_expires_at:
            return 0
        remaining = self.top_expires_at - datetime.utcnow()
        return max(0, remaining.days)

    def check_and_update_status(self):
        """Holatni tekshirish va yangilash"""
        if self.is_expired:
            self.is_active = False
            db.session.commit()
        if self.is_top_expired:
            self.is_top = False
            db.session.commit()


class PaymentRequest(db.Model):
    """PaymentRequest model - to'lov so'rovlari"""
    __tablename__ = 'payment_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # To'lov ma'lumotlari
    tariff_name = db.Column(db.String(50), default='KUMUSH')
    amount = db.Column(db.Integer)  # To'lov summasi

    # Chek ma'lumotlari
    receipt_file_id = db.Column(db.String(255))  # Telegram file_id
    receipt_message = db.Column(db.Text)  # Qo'shimcha xabar

    # Holat
    status = db.Column(db.String(20), default='pending')  # pending / approved / rejected

    # Admin
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_comment = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)

    # Vaqtlar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='payment_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    tariff = db.relationship('UserTariff', backref='payment_request', uselist=False)

    def __repr__(self):
        return f'<PaymentRequest {self.id} - {self.status}>'

    def approve(self, admin_id, comment=None):
        """To'lovni tasdiqlash"""
        self.status = 'approved'
        self.reviewed_by = admin_id
        self.review_comment = comment
        self.reviewed_at = datetime.utcnow()

        # Yangi tarif yaratish - tarif nomiga qarab
        from config import Config
        
        # TOP_xx maxsus tariflari (faqat TOP uchun, so'rovlar yo'q)
        if self.tariff_name and self.tariff_name.startswith('TOP_'):
            try:
                days = int(self.tariff_name.split('_', 1)[1])
            except (ValueError, IndexError):
                days = 1
            days = max(1, min(days, 30))
            requests_count = 0
            duration_days = days
            top_duration_days = days
            is_top = True
        elif self.tariff_name == 'KUMUSH':
            requests_count = Config.KUMUSH_TARIFF_REQUESTS
            duration_days = Config.KUMUSH_TARIFF_DAYS
            top_duration_days = Config.KUMUSH_TARIFF_TOP_DAYS
            is_top = False
        elif self.tariff_name == 'OLTIN':
            requests_count = Config.OLTIN_TARIFF_REQUESTS
            duration_days = Config.OLTIN_TARIFF_DAYS
            top_duration_days = Config.OLTIN_TARIFF_TOP_DAYS
            is_top = True
        elif self.tariff_name == 'VIP':
            requests_count = Config.VIP_TARIFF_REQUESTS
            duration_days = Config.VIP_TARIFF_DAYS
            top_duration_days = Config.VIP_TARIFF_TOP_DAYS
            is_top = True
        else:
            # Default KUMUSH
            requests_count = Config.KUMUSH_TARIFF_REQUESTS
            duration_days = Config.KUMUSH_TARIFF_DAYS
            top_duration_days = Config.KUMUSH_TARIFF_TOP_DAYS
            is_top = False
        
        new_tariff = UserTariff(
            user_id=self.user_id,
            tariff_name=self.tariff_name,
            requests_count=requests_count,
            total_requests=requests_count,
            duration_days=duration_days,
            top_duration_days=top_duration_days,
            is_top=is_top,
            payment_request_id=self.id
        )
        db.session.add(new_tariff)
        new_tariff.activate()

        db.session.commit()
        return new_tariff

    def reject(self, admin_id, comment=None):
        """To'lovni rad etish"""
        self.status = 'rejected'
        self.reviewed_by = admin_id
        self.review_comment = comment
        self.reviewed_at = datetime.utcnow()
        db.session.commit()
