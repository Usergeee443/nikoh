# NIKOH - Telegram Mini App

Halol va xavfsiz tanishuv platformasi Telegram Mini App sifatida.

## 📋 Loyiha haqida

NIKOH — Telegram Mini App bo'lib, bo'ydoq erkak va ayollarga halol, xavfsiz va vaqtinchalik muloqot orqali o'ziga mos juft topish imkonini beradi.

### Asosiy xususiyatlar

- ✅ Ochiq telefon raqam yo'q
- ✅ Ochiq ijtimoiy tarmoq yo'q
- ✅ Faqat maqsadli, vaqtinchalik chat (7 kun)
- ✅ So'rov yuborish pullik
- ✅ Tarif tizimi (KUMUSH tarif)
- ✅ Admin panel

## 🚀 Texnologiyalar

- **Backend**: Python Flask 3.0
- **Database**: SQLite (SQLAlchemy ORM)
- **Frontend**: HTML, Tailwind CSS
- **Bot**: python-telegram-bot 20.7
- **Mini App**: Telegram Web App SDK

## 📁 Loyiha strukturasi

```
nikoh/
├── app.py                 # Asosiy Flask application
├── config.py             # Konfiguratsiya
├── database.py           # Database sozlamalari
├── requirements.txt      # Python dependencies
├── .env.example         # Muhit o'zgaruvchilari namunasi
│
├── models/              # Database modellari
│   ├── user.py         # Foydalanuvchi modeli
│   ├── profile.py      # Profil modeli
│   ├── tariff.py       # Tarif modellari
│   ├── request.py      # So'rov modeli
│   └── chat.py         # Chat modellari
│
├── routes/              # API route'lar
│   ├── auth.py         # Autentifikatsiya
│   ├── profile.py      # Profil boshqaruvi
│   ├── feed.py         # E'lonlar feed
│   ├── tariff.py       # Tarif tizimi
│   ├── request.py      # So'rov tizimi
│   ├── chat.py         # Chat tizimi
│   └── admin.py        # Admin panel
│
├── telegram_bot/        # Telegram bot
│   └── bot.py          # Bot funksiyalari
│
├── templates/           # HTML shablonlar
│   ├── base.html       # Asosiy shablon
│   ├── feed.html       # E'lonlar sahifasi
│   ├── requests.html   # So'rovlar sahifasi
│   ├── onboarding/     # Ro'yxatdan o'tish sahifalari
│   ├── profile/        # Profil sahifalari
│   ├── chat/           # Chat sahifalari
│   └── admin/          # Admin panel sahifalari
│
└── static/              # Statik fayllar
    ├── css/
    └── js/
```

## 🛠️ O'rnatish

### 1. Talablar

- Python 3.8+
- pip
- Telegram Bot Token
- Virtual environment (tavsiya qilinadi)

### 2. O'rnatish qadamlari

```bash
# Repositoriyani klonlash
git clone <repository-url>
cd nikoh

# Virtual environment yaratish
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows

# Dependencylarni o'rnatish
pip install -r requirements.txt

# .env faylini yaratish
cp .env.example .env
# .env faylini tahrirlang va kerakli qiymatlarni kiriting
```

### 3. Muhit o'zgaruvchilarini sozlash

`.env` faylini yarating va quyidagi qiymatlarni kiriting:

```env
# Flask settings
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///nikoh.db

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# Mini App
MINI_APP_URL=https://your-domain.com

# Admin
ADMIN_TELEGRAM_IDS=123456789,987654321

# Payment
PAYMENT_CARD_NUMBER=8600 1234 5678 9012
PAYMENT_CARD_NAME=NIKOH APP
```

### 4. Ishga tushirish

```bash
# Development rejimida
python app.py

# Production rejimida (gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📱 Telegram Bot sozlash

### 1. BotFather orqali bot yaratish

1. Telegram'da [@BotFather](https://t.me/BotFather) botini oching
2. `/newbot` buyrug'ini yuboring
3. Bot nomi va username'ini kiriting
4. Bot token'ini oling

### 2. Web App sozlash

1. BotFather'da `/newapp` buyrug'ini yuboring
2. Botingizni tanlang
3. Web App URL'ini kiriting (masalan: `https://your-domain.com`)

### 3. Webhook sozlash

```python
# Webhook o'rnatish uchun
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/webhook"
```

## 💳 To'lov tizimi

Hozircha to'lov tizimi qo'lda ishlaydi:

1. Foydalanuvchi tarif tanlaydi
2. Karta raqami ko'rsatiladi
3. Foydalanuvchi to'lov qiladi va chekni botga yuklaydi
4. Admin tekshiradi va tasdiqlay di
5. Tarif faollashadi

## 🎯 Asosiy funksiyalar

### Profil yaratish

5 bosqichli onboarding jarayoni:
1. Shaxsiy ma'lumotlar
2. Jismoniy ma'lumotlar
3. Diniy ma'lumotlar
4. Ta'lim va kasb
5. Juftga qo'yiladigan talablar

### Tarif tizimi

**KUMUSH tarif:**
- 5 ta so'rov yuborish huquqi
- 10 kun davomida e'lon joylash
- E'lon 3 kun TOP da turadi
- Narx: 50,000 so'm

### So'rov yuborish

1. E'lonlarni ko'rish
2. Yoqqan profilga so'rov yuborish
3. Qarshi tomon qabul/rad qiladi
4. Qabul qilinsa 7 kunlik chat ochiladi

### Chat tizimi

- 7 kunlik vaqtinchalik chat
- Faqat text xabarlar (MVP)
- Muddat tugagach chat qulflanadi
- Faqat o'qish mumkin

## 👨‍💼 Admin panel

Admin panel orqali:
- Foydalanuvchilarni boshqarish
- To'lovlarni tasdiqlash/rad etish
- Statistikani ko'rish
- Foydalanuvchilarni bloklash

Admin panel: `/admin`

## 🔒 Xavfsizlik

- Ochiq telefon raqam va ijtimoiy tarmoqlar yo'q
- Faqat moderatsiya qilingan profil ma'lumotlari
- Report funksiyasi
- Admin moderation
- Session-based autentifikatsiya

## 📊 API Endpoints

### Autentifikatsiya
- `GET /` - Mini App kirish
- `GET /api/check-auth` - Autentifikatsiya tekshirish

### Profil
- `GET /profile/onboarding` - Onboarding boshlash
- `POST /profile/onboarding/step1` - 1-qadam
- `GET /profile/view` - Profilni ko'rish
- `POST /profile/edit` - Profilni tahrirlash
- `POST /profile/toggle-active` - E'lonni yoqish/o'chirish

### Feed
- `GET /feed` - E'lonlar sahifasi
- `GET /feed/api/listings` - E'lonlar ro'yxati
- `GET /feed/api/listing/<id>` - Bitta e'lon

### So'rovlar
- `GET /requests` - So'rovlar sahifasi
- `GET /requests/api/sent` - Yuborilgan so'rovlar
- `GET /requests/api/received` - Qabul qilingan so'rovlar
- `POST /requests/api/send` - So'rov yuborish
- `POST /requests/api/<id>/accept` - So'rovni qabul qilish
- `POST /requests/api/<id>/reject` - So'rovni rad etish

### Chat
- `GET /chat` - Chatlar ro'yxati
- `GET /chat/<id>` - Chat sahifasi
- `GET /chat/api/<id>/messages` - Chat xabarlari
- `POST /chat/api/<id>/send` - Xabar yuborish

### Tarif
- `GET /tariff/purchase` - Tarif sotib olish
- `GET /tariff/api/status` - Tarif holati

### Admin
- `GET /admin` - Admin panel
- `GET /admin/users` - Foydalanuvchilar
- `GET /admin/payments` - To'lovlar
- `POST /admin/api/payment/<id>/approve` - To'lovni tasdiqlash
- `POST /admin/api/payment/<id>/reject` - To'lovni rad etish

## 🐛 Debugging

```bash
# Loglarni ko'rish
tail -f app.log

# MySQL bilan ulanishni tekshirish (misol):
mysql -u nikoh_user -p nikoh
```

## 📝 Keyingi rejalar

- [ ] Rasm yuklash funksiyasi
- [ ] Media xabarlar (rasm, video)
- [ ] Qo'shimcha tariflar (OLTIN, PLATINUM)
- [ ] Avtomatik to'lov integratsiyasi (Click, Payme)
- [ ] Push bildirishnomalar
- [ ] Qidiruv va filterlar
- [ ] Sevimlilar ro'yxati
- [ ] Report tizimi
- [ ] Email bildirishnomalar
- [ ] Mobil ilovalar (iOS, Android)

## 👥 Hissa qo'shish

Pull request'lar xush kelibsiz! Katta o'zgarishlar uchun avval issue oching.

## 📄 Litsenziya

[MIT License](LICENSE)

## 📞 Aloqa

Savollar yoki takliflar uchun:
- Telegram: @your_username
- Email: your.email@example.com

---

**NIKOH** - Halol tanishuv platformasi 💚
