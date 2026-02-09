from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import User, Profile
from database import db
from datetime import datetime
from sqlalchemy import func

auth_bp = Blueprint('auth', __name__)

# /api/user-data uchun qisqa cache (30s) — takroriy so'rovlar tezroq
_user_data_cache = {}
_USER_DATA_CACHE_TTL = 30

def invalidate_user_data_cache(user_id):
    """Profil/tarif o'zgarganda cache ni tozalash."""
    _user_data_cache.pop(user_id, None)


@auth_bp.route('/')
def index():
    """Asosiy sahifa - Mini App"""
    # Telegram Web App ma'lumotlarini olish
    telegram_id = request.args.get('user_id')

    if not telegram_id:
        return render_template('error.html',
                             message="Iltimos, Telegram bot orqali kiring."), 403

    # Foydalanuvchini topish
    user = User.query.filter_by(telegram_id=int(telegram_id)).first()

    if not user:
        # Yangi foydalanuvchi yaratish
        user = User(telegram_id=int(telegram_id))
        db.session.add(user)
        db.session.commit()

    # Sessionga saqlash
    session['user_id'] = user.id
    session['telegram_id'] = telegram_id

    # Last active yangilash
    user.last_active = datetime.utcnow()
    db.session.commit()

    # Profil mavjudligini tekshirish
    if not user.profile:
        # Profil yaratish
        profile = Profile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    # Endi onboarding alohida HTML sahifalarda emas,
    # shuning uchun har doim SPA orqali ishlaymiz
    return render_template('spa.html', user=user)


@auth_bp.route('/api/user-data')
def get_user_data():
    """Foydalanuvchi ma'lumotlarini olish (SPA uchun) — eager load, 30s cache."""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Avtorizatsiya kerak'}), 401

    now = datetime.utcnow()
    cache_key = user_id
    if cache_key in _user_data_cache:
        cached_at, payload = _user_data_cache[cache_key]
        if (now - cached_at).total_seconds() < _USER_DATA_CACHE_TTL:
            return jsonify(payload)

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    # Profil, tarif va sent_requests count ni alohida so'rovlarda (property chaqirishdan qochish)
    from models.tariff import UserTariff
    from models import MatchRequest

    now = datetime.utcnow()
    profile = Profile.query.filter_by(user_id=user_id).order_by(
        Profile.is_primary.desc(), Profile.id
    ).first()

    active_tariff = UserTariff.query.filter(
        UserTariff.user_id == user_id,
        UserTariff.is_active == True,
        UserTariff.expires_at > now
    ).first()

    sent_requests_count = db.session.query(func.count(MatchRequest.id)).filter(
        MatchRequest.sender_id == user_id
    ).scalar() or 0

    profile_data = None
    if profile:
        profile_data = profile.to_dict()
        profile_data['partner_age_min'] = profile.partner_age_min
        profile_data['partner_age_max'] = profile.partner_age_max
        profile_data['partner_country'] = getattr(profile, 'partner_country', None)
        profile_data['partner_region'] = profile.partner_region
        profile_data['partner_religious_level'] = profile.partner_religious_level
        profile_data['partner_marital_status'] = profile.partner_marital_status

    tariff_data = None
    if active_tariff:
        tariff_data = {
            'has_active_tariff': True,
            'tariff': {
                'name': active_tariff.tariff_name,
                'requests_count': active_tariff.requests_count,
                'total_requests': active_tariff.total_requests,
                'is_top': active_tariff.is_top and not active_tariff.is_top_expired,
                'days_remaining': active_tariff.days_remaining,
                'expires_at': active_tariff.expires_at.isoformat() if active_tariff.expires_at else None
            }
        }
    else:
        tariff_data = {'has_active_tariff': False, 'tariff': None}

    profile_basic_complete = profile.basic_complete if profile else False
    profile_complete = profile.is_complete if profile else False
    profile_active = profile.is_active if profile else False

    payload = {
        'user': {
            'id': user.id,
            'telegram_id': user.telegram_id,
            'profile_basic_complete': profile_basic_complete,
            'profile_complete': profile_complete,
            'profile_active': profile_active,
            'has_active_tariff': active_tariff is not None,
            'sent_requests_count': sent_requests_count
        },
        'profile': profile_data,
        'tariff': tariff_data
    }
    _user_data_cache[cache_key] = (now, payload)
    return jsonify(payload)


@auth_bp.route('/logout')
def logout():
    """Sessionni tozalash va asosiy sahifaga yo'naltirish."""
    session.clear()
    return redirect(url_for('auth.index'))


@auth_bp.route('/api/check-auth')
def check_auth():
    """Foydalanuvchi autentifikatsiyasini tekshirish"""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'authenticated': False}), 401

    user = User.query.get(user_id)

    if not user:
        return jsonify({'authenticated': False}), 401

    return jsonify({
        'authenticated': True,
        'user_id': user.id,
        'telegram_id': user.telegram_id,
        'profile_basic_complete': user.profile_basic_completed,
        'profile_complete': user.profile_completed,
        'profile_active': user.profile.is_active if user.profile else False,
        'has_active_tariff': user.has_active_tariff
    })


def login_required(f):
    """Login talab qiluvchi decorator"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.index'))

        user = User.query.get(session['user_id'])
        if not user:
            return redirect(url_for('auth.index'))

        return f(*args, **kwargs)

    return decorated_function


def basic_profile_required(f):
    """Minimal ro'yxatdan o'tish talab qiluvchi (e'lon ko'rish, sevimliga saqlash uchun)"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.index'))

        user = User.query.get(session['user_id'])
        if not user or not user.profile_basic_completed:
            return redirect(url_for('auth.index'))

        return f(*args, **kwargs)

    return decorated_function


def profile_required(f):
    """To'liq profil talab qiluvchi decorator (so'rov yuborish, e'lon joylash uchun)"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.index'))

        user = User.query.get(session['user_id'])
        if not user or not user.profile_completed:
            return redirect(url_for('profile.view'))

        return f(*args, **kwargs)

    return decorated_function
