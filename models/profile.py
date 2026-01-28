from database import db
from datetime import datetime


class Profile(db.Model):
    """Profile model - foydalanuvchi profili"""
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)

    # 5.1 Shaxsiy ma'lumotlar
    name = db.Column(db.String(100))
    gender = db.Column(db.String(10))  # Erkak / Ayol
    birth_year = db.Column(db.Integer)
    region = db.Column(db.String(100))  # Viloyat/Shahar
    nationality = db.Column(db.String(50))
    marital_status = db.Column(db.String(20))  # Bo'ydoq / Ajrashgan

    # 5.2 Jismoniy ma'lumotlar
    height = db.Column(db.Integer)  # Bo'y (sm)
    weight = db.Column(db.Integer)  # Vazn (kg)

    # 5.3 Diniy ma'lumotlar
    prays = db.Column(db.String(20))  # Doimiy / Ba'zan / O'qimaydi
    fasts = db.Column(db.String(10))  # Ha / Yo'q
    religious_level = db.Column(db.String(20))  # Past / O'rtacha / Yuqori

    # 5.4 Ta'lim va kasb
    education = db.Column(db.String(100))
    profession = db.Column(db.String(100))
    is_working = db.Column(db.Boolean)

    # 5.5 Juftga qo'yiladigan talablar
    partner_age_min = db.Column(db.Integer)
    partner_age_max = db.Column(db.Integer)
    partner_region = db.Column(db.String(100))
    partner_religious_level = db.Column(db.String(20))
    partner_marital_status = db.Column(db.String(20))

    # 6. E'lon ma'lumotlari
    bio = db.Column(db.Text)  # Qisqa tavsif
    is_active = db.Column(db.Boolean, default=False)  # E'lon aktiv/passiv
    activated_at = db.Column(db.DateTime)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Profile {self.name}>'

    @property
    def is_complete(self):
        """Profil to'liq to'ldirilganmi?"""
        required_fields = [
            self.name, self.gender, self.birth_year, self.region,
            self.nationality, self.marital_status, self.height, self.weight,
            self.prays, self.fasts, self.religious_level,
            self.education, self.profession, self.is_working is not None,
            self.partner_age_min, self.partner_age_max,
            self.partner_region, self.partner_religious_level,
            self.partner_marital_status
        ]
        return all(required_fields)

    @property
    def age(self):
        """Yoshni hisoblash"""
        if self.birth_year:
            current_year = datetime.utcnow().year
            return current_year - self.birth_year
        return None

    @property
    def completion_percentage(self):
        """Profil to'liq to'ldirilganlik foizi"""
        total_fields = 19
        filled_fields = sum([
            bool(self.name),
            bool(self.gender),
            bool(self.birth_year),
            bool(self.region),
            bool(self.nationality),
            bool(self.marital_status),
            bool(self.height),
            bool(self.weight),
            bool(self.prays),
            bool(self.fasts),
            bool(self.religious_level),
            bool(self.education),
            bool(self.profession),
            self.is_working is not None,
            bool(self.partner_age_min),
            bool(self.partner_age_max),
            bool(self.partner_region),
            bool(self.partner_religious_level),
            bool(self.partner_marital_status)
        ])
        return int((filled_fields / total_fields) * 100)

    def activate(self):
        """E'lonni faollashtirish"""
        self.is_active = True
        self.activated_at = datetime.utcnow()
        db.session.commit()

    def deactivate(self):
        """E'lonni deaktiv qilish"""
        self.is_active = False
        db.session.commit()

    def to_dict(self):
        """Profilni dictionary ga aylantirish"""
        # Generate unique gradient background based on user_id
        import hashlib
        user_id_str = str(self.user_id)
        hash_value = int(hashlib.md5(user_id_str.encode()).hexdigest()[:8], 16)
        
        # Generate gradient colors based on hash
        colors = [
            ['#FF6B6B', '#4ECDC4'], ['#45B7D1', '#96CEB4'], ['#FFEAA7', '#DDA0DD'],
            ['#74B9FF', '#A29BFE'], ['#FD79A8', '#FDCB6E'], ['#6C5CE7', '#A29BFE'],
            ['#00B894', '#00CEC9'], ['#E17055', '#FDCB6E'], ['#0984E3', '#74B9FF'],
            ['#6C5CE7', '#A29BFE']
        ]
        color_pair = colors[hash_value % len(colors)]
        
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'region': self.region,
            'location': self.region,  # Alias for region
            'nationality': self.nationality,
            'marital_status': self.marital_status,
            'height': self.height,
            'weight': self.weight,
            'prays': self.prays,
            'fasts': self.fasts,
            'religious_level': self.religious_level,
            'education': self.education,
            'profession': self.profession,
            'is_working': self.is_working,
            'bio': self.bio,
            'is_active': self.is_active,
            'completion_percentage': self.completion_percentage,
            'partner_age_min': self.partner_age_min,
            'partner_age_max': self.partner_age_max,
            'partner_region': self.partner_region,
            'partner_religious_level': self.partner_religious_level,
            'partner_marital_status': self.partner_marital_status,
            'photo_url': None,  # Will be generated on frontend using gradient
            'salary': None,  # Not stored in profile, will be calculated if needed
            'views_count': 0,  # Placeholder
            'favorites_count': 0  # Placeholder
        }
