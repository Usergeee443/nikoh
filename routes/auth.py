from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import User, Profile
from database import db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


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

    # Profil to'liqligini tekshirish
    if not user.profile.is_complete:
        return redirect(url_for('profile.onboarding'))

    # E'lon aktiv emasligini tekshirish
    if not user.profile.is_active:
        return redirect(url_for('profile.activate_profile'))

    # Asosiy sahifaga yo'naltirish (Feed)
    return redirect(url_for('feed.index'))


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


def profile_required(f):
    """To'liq profil talab qiluvchi decorator"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.index'))

        user = User.query.get(session['user_id'])
        if not user or not user.profile_completed:
            return redirect(url_for('profile.onboarding'))

        return f(*args, **kwargs)

    return decorated_function
