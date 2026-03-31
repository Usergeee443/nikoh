from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, current_app
from models import User, Profile
from database import db
from datetime import datetime
from sqlalchemy import func
import hmac
import hashlib
from urllib.parse import unquote, parse_qs

auth_bp = Blueprint('auth', __name__)

_user_data_cache = {}
_USER_DATA_CACHE_TTL = 30

def invalidate_user_data_cache(user_id):
    _user_data_cache.pop(user_id, None)


def _validate_telegram_init_data(init_data_raw, bot_token):
    """Telegram Mini App initData ni tekshirish va user id qaytarish. Xato bo'lsa None."""
    if not init_data_raw or not bot_token:
        return None
    try:
        parsed = parse_qs(unquote(init_data_raw), keep_blank_values=True)
        hash_val = (parsed.get('hash') or [None])[0]
        if not hash_val:
            return None
        data_pairs = sorted((k, (v[0] if isinstance(v, list) else v)) for k, v in parsed.items() if k != 'hash')
        data_check_string = '\n'.join(f'{k}={v}' for k, v in data_pairs)
        secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated, hash_val):
            return None
        import json
        user_json = (parsed.get('user') or [None])[0]
        if not user_json:
            return None
        user_obj = json.loads(user_json)
        return int(user_obj.get('id'))
    except Exception:
        return None


def _ensure_user_and_session(telegram_id):
    """telegram_id bo'yicha user topish/yaratish, session o'rnatish, profil yaratish. user qaytaradi."""
    user = User.query.filter_by(telegram_id=int(telegram_id)).first()
    if not user:
        user = User(telegram_id=int(telegram_id))
        db.session.add(user)
        db.session.commit()
    session['user_id'] = user.id
    session['telegram_id'] = str(telegram_id)
    user.last_active = datetime.utcnow()
    db.session.commit()
    if not user.profile:
        profile = Profile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return user


@auth_bp.route('/auth/telegram-login', methods=['POST'])
def telegram_login():
    """Telegram Mini App initData orqali kirish (bot orqali ochilganda)."""
    data = request.get_json(silent=True) or {}
    init_data = (data.get('init_data') or '').strip()
    token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    if not token:
        return jsonify({'success': False, 'error': 'Server sozlamasi xato'}), 500
    telegram_id = _validate_telegram_init_data(init_data, token)
    if not telegram_id:
        return jsonify({'success': False, 'error': 'Telegram ma\'lumotlari noto\'g\'ri'}), 400
    _ensure_user_and_session(telegram_id)
    return jsonify({'success': True})


@auth_bp.route('/')
def index():
    """Asosiy sahifa - Mini App. user_id URL da bo'lsa yoki session bo'lsa SPA, aks holda SPA (initData orqali keyin login)."""
    telegram_id = request.args.get('user_id')

    if telegram_id:
        user = _ensure_user_and_session(telegram_id)
        return render_template('spa.html', user=user)

    # URL da user_id yo'q: session bormi tekshirish (ilgari telegram-login orqali kirgan bo'lishi mumkin)
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return render_template('spa.html', user=user)

    # Yangi foydalanuvchi: SPA yuklanadi, frontend initData yuborib /auth/telegram-login qiladi va sahifani yangilaydi
    return render_template('spa.html', user=None)


@auth_bp.route('/api/user-data')
def get_user_data():
    """Foydalanuvchi ma'lumotlarini olish (SPA uchun) — eager load, 30s cache. ?refresh=1 cache'ni chetlab o'tadi."""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'error': 'Avtorizatsiya kerak'}), 401

    force_refresh = request.args.get('refresh') == '1'
    now = datetime.utcnow()
    cache_key = user_id
    if not force_refresh and cache_key in _user_data_cache:
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
