from database import db
from datetime import datetime


class Profile(db.Model):
    """Profile model - foydalanuvchi profili"""
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # bir user bir nechta e'lon (profil) yarata oladi
    is_primary = db.Column(db.Boolean, default=True)  # asosiy profil (o'zi) yoki qo'shimcha (aka/opa uchun)

    # 5.1 Shaxsiy ma'lumotlar
    phone_number = db.Column(db.String(20))  # Telefon raqam (oddiy ro'yxatdan o'tish)
    name = db.Column(db.String(100))
    gender = db.Column(db.String(10), index=True)  # Erkak / Ayol
    birth_year = db.Column(db.Integer)
    country = db.Column(db.String(100))  # Davlat (O'zbekiston, Rossiya, Turkiya, ...)
    region = db.Column(db.String(100))  # Viloyat/Shahar (davlat bo'yicha)
    nationality = db.Column(db.String(50))
    current_residence = db.Column(db.String(200))  # Hozir qayerda yashashi (millat/davlat/shavardan tashqari)
    marital_status = db.Column(db.String(20))  # Bo'ydoq / Ajrashgan

    # 5.2 Jismoniy ma'lumotlar
    height = db.Column(db.Integer)  # Bo'y (sm)
    weight = db.Column(db.Integer)  # Vazn (kg)
    smoking = db.Column(db.String(20))  # Ha / Yo'q / Tashlagan
    sport_days = db.Column(db.Integer)  # Haftada necha kun sport (0-7)

    # 5.3 Diniy ma'lumotlar (aqida, namoz, qur'on o'qish, mazhab)
    aqida = db.Column(db.String(50))  # Ahli Sunna, Ash'ariya, Moturidiya, Boshqa
    prays = db.Column(db.String(20))  # Namoz: Ha / Ba'zan / Yo'q
    fasts = db.Column(db.String(10))  # Ro'za: Ha / Yo'q
    quran_reading = db.Column(db.String(50))  # Bilmaydi, O'qishni biladi, Ravon o'qiydi, Hofizi Qur'on
    mazhab = db.Column(db.String(30))  # Hanafi, Shafi'i, Maliki, Hanbali
    religious_level = db.Column(db.String(20))  # Jiddiy / O'rtacha / Yengil

    # 5.4 Ta'lim va kasb
    education = db.Column(db.String(100))
    profession = db.Column(db.String(100))
    is_working = db.Column(db.Boolean)
    salary = db.Column(db.String(100))  # Maosh (masalan: "500$", "3-5 mln")

    # 5.5 Juftga qo'yiladigan talablar
    partner_age_min = db.Column(db.Integer)
    partner_age_max = db.Column(db.Integer)
    partner_country = db.Column(db.String(100))  # Juftga davlat (legacy, bitta)
    partner_region = db.Column(db.String(100))   # Juftga viloyat/sahar (legacy)
    partner_locations = db.Column(db.Text)  # JSON: [{"c":"Davlat","r":["shahar"]} yoki {"c":"Davlat","all":true}]
    partner_religious_level = db.Column(db.String(20))
    partner_marital_status = db.Column(db.String(20))

    # 6. E'lon ma'lumotlari
    bio = db.Column(db.Text)  # Qisqa tavsif
    is_active = db.Column(db.Boolean, default=False, index=True)  # E'lon aktiv/passiv
    is_published = db.Column(db.Boolean, default=False, index=True)  # E'lon qilingan/qoralama
    moderation_status = db.Column(db.String(20), default='pending', index=True)  # pending, approved, rejected
    activated_at = db.Column(db.DateTime, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Profile {self.name}>'

    @property
    def basic_complete(self):
        """Minimal ro'yxatdan o'tish: telefon, ism, yosh, jins (e'lon ko'rish va sevimliga saqlash uchun)"""
        return bool(self.phone_number and self.name and self.gender and self.birth_year)

    def _filled(self, val):
        """String bo'lsa bo'sh emasligini, boshqa turlar uchun truthy tekshirish"""
        if val is None:
            return False
        if isinstance(val, str):
            return bool(val.strip())
        return True

    @property
    def is_complete(self):
        """Profil to'liq to'ldirilganmi? (so'rov yuborish va e'lon joylash uchun)"""
        loc_ok = self._partner_locations_ok()
        required_fields = [
            self._filled(self.name), self._filled(self.gender), self.birth_year is not None,
            self._filled(self.region), self._filled(self.nationality),
            self._filled(getattr(self, 'current_residence', None)),
            self._filled(self.marital_status), self.height is not None, self.weight is not None,
            self._filled(self.prays), self._filled(self.fasts), self._filled(self.religious_level),
            self._filled(self.education), self._filled(self.profession), self.is_working is not None,
            self.partner_age_min is not None, self.partner_age_max is not None,
            loc_ok,
            self._filled(self.partner_religious_level), self._filled(self.partner_marital_status)
        ]
        return all(required_fields)

    def _partner_locations_ok(self):
        """Juftga joylashuv to'ldirilganmi: partner_locations yoki legacy (partner_region yoki partner_country+partner_region).
        Onboarding formada faqat partner_region bor, shuning uchun partner_region bitta to'ldirilganda ham qabul qilinadi."""
        locs = getattr(self, 'partner_locations', None)
        if locs:
            try:
                import json
                arr = json.loads(locs) if isinstance(locs, str) else locs
                if isinstance(arr, list) and len(arr) > 0:
                    return True
            except Exception:
                pass
        if self._filled(self.partner_region):
            return True
        return bool(self._filled(getattr(self, 'partner_country', None)) and self._filled(self.partner_region))

    def _get_partner_locations_list(self):
        """API uchun juftga joylashuv ro'yxati: [{"c":"Davlat","r":[...]} yoki {"c":"...","all":true}]"""
        locs = getattr(self, 'partner_locations', None)
        if locs:
            try:
                import json
                arr = json.loads(locs) if isinstance(locs, str) else locs
                if isinstance(arr, list) and len(arr) > 0:
                    return arr
            except Exception:
                pass
        pc = getattr(self, 'partner_country', None)
        if pc and self.partner_region:
            return [{'c': pc, 'r': [self.partner_region]}]
        return []

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

    def to_card_dict(self):
        """So'rovlar / ro'yxatlar uchun yengil JSON (to_dict dan tezroq, kichikroq)."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'region': self.region,
            'location': self.region,
            'nationality': self.nationality,
            'country': self.country,
            'current_residence': getattr(self, 'current_residence', None),
            'marital_status': self.marital_status,
            'bio': (self.bio[:280] + '…') if self.bio and len(self.bio) > 280 else self.bio,
            'photo_url': None,
            'is_active': self.is_active,
        }

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
            'phone_number': self.phone_number,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'region': self.region,
            'location': self.region,  # Alias for region
            'nationality': self.nationality,
            'current_residence': getattr(self, 'current_residence', None),
            'marital_status': self.marital_status,
            'height': self.height,
            'weight': self.weight,
            'smoking': getattr(self, 'smoking', None),
            'sport_days': getattr(self, 'sport_days', None),
            'aqida': self.aqida,
            'prays': self.prays,
            'fasts': self.fasts,
            'quran_reading': self.quran_reading,
            'mazhab': self.mazhab,
            'religious_level': self.religious_level,
            'education': self.education,
            'profession': self.profession,
            'is_working': self.is_working,
            'salary': self.salary,
            'bio': self.bio,
            'is_active': self.is_active,
            'is_published': self.is_published,
            'moderation_status': getattr(self, 'moderation_status', None),
            'birth_year': self.birth_year,
            'completion_percentage': self.completion_percentage,
            'partner_age_min': self.partner_age_min,
            'partner_age_max': self.partner_age_max,
            'partner_country': getattr(self, 'partner_country', None),
            'partner_region': self.partner_region,
            'partner_locations': self._get_partner_locations_list(),
            'partner_religious_level': self.partner_religious_level,
            'partner_marital_status': self.partner_marital_status,
            'photo_url': None,  # Will be generated on frontend using gradient
            'country': self.country,
            'views_count': 0,  # Placeholder
            'favorites_count': 0  # Placeholder
        }
