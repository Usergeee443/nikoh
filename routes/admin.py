from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, current_app
from models import User, Profile, PaymentRequest, UserTariff, MatchRequest, Chat, Setting
from database import db
from routes.auth import login_required, _ensure_user_and_session, invalidate_user_data_cache
from functools import wraps
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _safe_delete_profile(profile_id):
    """Profilni o'chirish: boshqa jadvallardagi FK larni avval null qilish."""
    profile = Profile.query.get(profile_id)
    if not profile:
        return False, 'Profil topilmadi'
    pid = profile.id
    MatchRequest.query.filter_by(receiver_profile_id=pid).update({'receiver_profile_id': None})
    Chat.query.filter_by(profile1_id=pid).update({'profile1_id': None})
    Chat.query.filter_by(profile2_id=pid).update({'profile2_id': None})
    db.session.delete(profile)
    db.session.commit()
    return True, None


@admin_bp.before_request
def admin_login_via_user_id():
    """Telegramdan /admin?user_id=TELEGRAM_ID ochilganda session yo'q bo'lsa, admin bo'lsa session yaratib admin panelda qolish."""
    if 'user_id' in session:
        return None  # allaqachon kirgan
    q = request.args.get('user_id', '').strip()
    if not q:
        return None
    try:
        telegram_id = int(q)
    except ValueError:
        return None
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user or not user.is_admin:
        return None
    _ensure_user_and_session(telegram_id)
    # URL dan user_id ni olib tashlash (xavfsizlik va toza URL)
    return redirect(request.path)


def admin_required(f):
    """Admin huquqi talab qiluvchi decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.index'))

        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return render_template('error.html',
                                 message='Sizda admin huquqi yo\'q'), 403

        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/')
@admin_required
def index():
    """Admin panel asosiy sahifa"""
    user = User.query.get(session['user_id'])

    # Statistika
    pending_moderation = Profile.query.filter(Profile.moderation_status == 'pending').count() if hasattr(Profile, 'moderation_status') else 0
    stats = {
        'total_users': User.query.count(),
        'active_profiles': Profile.query.filter_by(is_active=True).count(),
        'pending_payments': PaymentRequest.query.filter_by(status='pending').count(),
        'pending_moderation': pending_moderation,
        'active_chats': Chat.query.filter_by(is_active=True).count(),
        'total_requests': MatchRequest.query.count()
    }

    mini_app_url = current_app.config.get('MINI_APP_URL', '') or ''
    return render_template('admin/index.html',
                         user=user,
                         stats=stats,
                         mini_app_url=mini_app_url)


@admin_bp.route('/users')
@admin_required
def users():
    """Foydalanuvchilar ro'yxati"""
    user = User.query.get(session['user_id'])

    page = request.args.get('page', 1, type=int)
    per_page = 50

    users_query = User.query.order_by(User.created_at.desc())
    pagination = users_query.paginate(page=page, per_page=per_page, error_out=False)

    mini_app_url = current_app.config.get('MINI_APP_URL', '') or ''
    return render_template('admin/users.html',
                         user=user,
                         users=pagination.items,
                         pagination=pagination,
                         mini_app_url=mini_app_url)


@admin_bp.route('/payments')
@admin_required
def payments():
    """To'lov so'rovlari"""
    user = User.query.get(session['user_id'])

    status_filter = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = PaymentRequest.query

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    query = query.order_by(PaymentRequest.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    mini_app_url = current_app.config.get('MINI_APP_URL', '') or ''
    return render_template('admin/payments.html',
                         user=user,
                         payments=pagination.items,
                         pagination=pagination,
                         status_filter=status_filter,
                         mini_app_url=mini_app_url)


@admin_bp.route('/api/user/<int:user_id>/block', methods=['POST'])
@admin_required
def block_user(user_id):
    """Foydalanuvchini bloklash"""
    target_user = User.query.get(user_id)

    if not target_user:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    target_user.is_blocked = True
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Foydalanuvchi bloklandi'
    })


@admin_bp.route('/api/user/<int:user_id>/unblock', methods=['POST'])
@admin_required
def unblock_user(user_id):
    """Foydalanuvchini blokdan chiqarish"""
    target_user = User.query.get(user_id)

    if not target_user:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    target_user.is_blocked = False
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Foydalanuvchi blokdan chiqarildi'
    })


@admin_bp.route('/api/payment/<int:payment_id>/approve', methods=['POST'])
@admin_required
def approve_payment(payment_id):
    """To'lovni tasdiqlash"""
    admin_user = User.query.get(session['user_id'])
    payment = PaymentRequest.query.get(payment_id)

    if not payment:
        return jsonify({'error': 'To\'lov topilmadi'}), 404

    if payment.status != 'pending':
        return jsonify({'error': 'Bu to\'lov allaqachon qayta ishlangan'}), 400

    data = request.get_json()
    comment = data.get('comment', '')

    # To'lovni tasdiqlash
    tariff = payment.approve(admin_user.id, comment)
    invalidate_user_data_cache(payment.user_id)

    return jsonify({
        'success': True,
        'message': 'To\'lov tasdiqlandi',
        'tariff_id': tariff.id
    })


@admin_bp.route('/api/payment/<int:payment_id>/reject', methods=['POST'])
@admin_required
def reject_payment(payment_id):
    """To'lovni rad etish"""
    admin_user = User.query.get(session['user_id'])
    payment = PaymentRequest.query.get(payment_id)

    if not payment:
        return jsonify({'error': 'To\'lov topilmadi'}), 404

    if payment.status != 'pending':
        return jsonify({'error': 'Bu to\'lov allaqachon qayta ishlangan'}), 400

    data = request.get_json()
    comment = data.get('comment', 'Admin tomonidan rad etildi')

    # To'lovni rad etish
    payment.reject(admin_user.id, comment)

    return jsonify({
        'success': True,
        'message': 'To\'lov rad etildi'
    })


# ——— Moderatsiya (e'lonlar) ———
@admin_bp.route('/moderation')
@admin_required
def moderation():
    """E'lonlar moderatsiyasi — User bilan bir so'rovda (N+1 yo'q)."""
    user = User.query.get(session['user_id'])
    status_filter = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = 15
    query = Profile.query.options(joinedload(Profile.user))
    if hasattr(Profile, 'moderation_status'):
        if status_filter == 'pending':
            query = query.filter(Profile.moderation_status == 'pending')
        elif status_filter == 'approved':
            query = query.filter(Profile.moderation_status == 'approved')
        elif status_filter == 'rejected':
            query = query.filter(Profile.moderation_status == 'rejected')
    query = query.order_by(Profile.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    mini_app_url = current_app.config.get('MINI_APP_URL', '') or ''
    return render_template('admin/moderation.html',
                         user=user,
                         profiles=pagination.items,
                         pagination=pagination,
                         status_filter=status_filter,
                         mini_app_url=mini_app_url)


@admin_bp.route('/api/moderation/<int:profile_id>/approve', methods=['POST'])
@admin_required
def approve_moderation(profile_id):
    """E'lonni tasdiqlash (moderatsiya)"""
    profile = Profile.query.get(profile_id)
    if not profile:
        return jsonify({'error': 'E\'lon topilmadi'}), 404
    if getattr(profile, 'moderation_status', None) != 'pending':
        return jsonify({'error': 'E\'lon allaqachon ko\'rib chiqilgan'}), 400
    profile.moderation_status = 'approved'
    profile.is_active = True
    if not profile.activated_at:
        profile.activated_at = datetime.utcnow()
    db.session.commit()
    invalidate_user_data_cache(profile.user_id)
    return jsonify({'success': True, 'message': 'E\'lon tasdiqlandi'})


@admin_bp.route('/api/moderation/<int:profile_id>/reject', methods=['POST'])
@admin_required
def reject_moderation(profile_id):
    """E'lonni rad etish (moderatsiya)"""
    profile = Profile.query.get(profile_id)
    if not profile:
        return jsonify({'error': 'E\'lon topilmadi'}), 404
    if getattr(profile, 'moderation_status', None) != 'pending':
        return jsonify({'error': 'E\'lon allaqachon ko\'rib chiqilgan'}), 400
    profile.moderation_status = 'rejected'
    profile.is_active = False
    db.session.commit()
    invalidate_user_data_cache(profile.user_id)
    return jsonify({'success': True, 'message': 'E\'lon rad etildi'})


@admin_bp.route('/api/profile/<int:profile_id>/block-user', methods=['POST'])
@admin_required
def block_user_by_profile(profile_id):
    """Profil egasini (foydalanuvchini) bloklash."""
    profile = Profile.query.get(profile_id)
    if not profile:
        return jsonify({'error': 'Profil topilmadi'}), 404
    u = User.query.get(profile.user_id)
    if not u:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404
    u.is_blocked = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Foydalanuvchi bloklandi'})


@admin_bp.route('/api/profile/<int:profile_id>', methods=['DELETE'])
@admin_required
def delete_profile_admin(profile_id):
    """E'lonni (profil yozuvini) o'chirish — bog'liq so'rov/chat FK lari avval tozalanadi."""
    ok, err = _safe_delete_profile(profile_id)
    if not ok:
        return jsonify({'error': err}), 404
    return jsonify({'success': True, 'message': 'E\'lon o\'chirildi'})


# ——— Tarif narxlari (sozlamalar) ———
def _get_tariff_setting(key, default):
    from config import Config
    val = Setting.get(key) if Setting else None
    if val is not None and val != '':
        try:
            return int(val)
        except ValueError:
            pass
    return getattr(Config, key, default)


@admin_bp.route('/settings')
@admin_required
def settings_page():
    """Tarif va reklama narxlari"""
    user = User.query.get(session['user_id'])
    from config import Config
    prices = {
        'KUMUSH_TARIFF_PRICE': _get_tariff_setting('KUMUSH_TARIFF_PRICE', getattr(Config, 'KUMUSH_TARIFF_PRICE', 50000)),
        'OLTIN_TARIFF_PRICE': _get_tariff_setting('OLTIN_TARIFF_PRICE', getattr(Config, 'OLTIN_TARIFF_PRICE', 100000)),
        'VIP_TARIFF_PRICE': _get_tariff_setting('VIP_TARIFF_PRICE', getattr(Config, 'VIP_TARIFF_PRICE', 250000)),
        'TOP_7_PRICE': _get_tariff_setting('TOP_7_PRICE', 15000),
        'TOP_30_PRICE': _get_tariff_setting('TOP_30_PRICE', 30000),
    }
    mini_app_url = current_app.config.get('MINI_APP_URL', '') or ''
    return render_template('admin/settings.html', user=user, prices=prices, mini_app_url=mini_app_url)


@admin_bp.route('/api/settings/tariff', methods=['GET', 'POST'])
@admin_required
def api_settings_tariff():
    """Tarif narxlari (GET) yoki yangilash (POST). Bepul qilish: 0 yuboring."""
    if request.method == 'GET':
        from config import Config
        return jsonify({
            'KUMUSH_TARIFF_PRICE': _get_tariff_setting('KUMUSH_TARIFF_PRICE', getattr(Config, 'KUMUSH_TARIFF_PRICE', 50000)),
            'OLTIN_TARIFF_PRICE': _get_tariff_setting('OLTIN_TARIFF_PRICE', getattr(Config, 'OLTIN_TARIFF_PRICE', 100000)),
            'VIP_TARIFF_PRICE': _get_tariff_setting('VIP_TARIFF_PRICE', getattr(Config, 'VIP_TARIFF_PRICE', 250000)),
            'TOP_7_PRICE': _get_tariff_setting('TOP_7_PRICE', 15000),
            'TOP_30_PRICE': _get_tariff_setting('TOP_30_PRICE', 30000),
        })
    data = request.get_json() or {}
    for key in ('KUMUSH_TARIFF_PRICE', 'OLTIN_TARIFF_PRICE', 'VIP_TARIFF_PRICE', 'TOP_7_PRICE', 'TOP_30_PRICE'):
        if key in data:
            try:
                v = int(data[key])
                if v < 0:
                    v = 0
                Setting.set(key, v)
            except (ValueError, TypeError):
                pass
    return jsonify({'success': True, 'message': 'Narxlar yangilandi'})


# ——— Adminlar ro'yxati va yangi admin qo'shish ———
@admin_bp.route('/admins')
@admin_required
def admins_list():
    """Adminlar ro'yxati"""
    user = User.query.get(session['user_id'])
    admins = User.query.filter(User.is_admin == True).order_by(User.id).all()
    mini_app_url = current_app.config.get('MINI_APP_URL', '') or ''
    return render_template('admin/admins.html', user=user, admins=admins, mini_app_url=mini_app_url)


@admin_bp.route('/api/admins', methods=['POST'])
@admin_required
def api_add_admin():
    """Yangi admin qo'shish (telegram_id orqali). Body: {"telegram_id": 123456789}"""
    data = request.get_json() or {}
    try:
        tid = int(data.get('telegram_id') or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'telegram_id (raqam) kerak'}), 400
    if not tid:
        return jsonify({'error': 'telegram_id bo\'sh bo\'lmasin'}), 400
    u = User.query.filter_by(telegram_id=tid).first()
    if not u:
        u = User(telegram_id=tid, is_admin=True)
        db.session.add(u)
        db.session.commit()
    else:
        u.is_admin = True
        db.session.commit()
    return jsonify({'success': True, 'message': f'Admin qo\'shildi: {tid}', 'user_id': u.id})


@admin_bp.route('/statistics')
@admin_required
def statistics():
    """Statistika"""
    user = User.query.get(session['user_id'])

    # Umumiy statistika
    stats = {
        'total_users': User.query.count(),
        'total_profiles': Profile.query.count(),
        'active_profiles': Profile.query.filter_by(is_active=True).count(),
        'inactive_profiles': Profile.query.filter_by(is_active=False).count(),

        'male_profiles': Profile.query.filter_by(gender='Erkak').count(),
        'female_profiles': Profile.query.filter_by(gender='Ayol').count(),

        'total_tariffs': UserTariff.query.count(),
        'active_tariffs': UserTariff.query.filter_by(is_active=True).count(),

        'total_payments': PaymentRequest.query.count(),
        'pending_payments': PaymentRequest.query.filter_by(status='pending').count(),
        'approved_payments': PaymentRequest.query.filter_by(status='approved').count(),
        'rejected_payments': PaymentRequest.query.filter_by(status='rejected').count(),

        'total_requests': MatchRequest.query.count(),
        'pending_requests': MatchRequest.query.filter_by(status='pending').count(),
        'accepted_requests': MatchRequest.query.filter_by(status='accepted').count(),
        'rejected_requests': MatchRequest.query.filter_by(status='rejected').count(),

        'total_chats': Chat.query.count(),
        'active_chats': Chat.query.filter_by(is_active=True).count()
    }

    # Hududlar bo'yicha statistika
    region_stats = db.session.query(
        Profile.region,
        func.count(Profile.id)
    ).group_by(Profile.region).all()

    mini_app_url = current_app.config.get('MINI_APP_URL', '') or ''
    return render_template('admin/statistics.html',
                         user=user,
                         stats=stats,
                         region_stats=region_stats,
                         mini_app_url=mini_app_url)
