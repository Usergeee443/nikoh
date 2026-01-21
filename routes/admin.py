from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from models import User, Profile, PaymentRequest, UserTariff, MatchRequest, Chat
from database import db
from routes.auth import login_required
from functools import wraps
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


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
    stats = {
        'total_users': User.query.count(),
        'active_profiles': Profile.query.filter_by(is_active=True).count(),
        'pending_payments': PaymentRequest.query.filter_by(status='pending').count(),
        'active_chats': Chat.query.filter_by(is_active=True).count(),
        'total_requests': MatchRequest.query.count()
    }

    return render_template('admin/index.html',
                         user=user,
                         stats=stats)


@admin_bp.route('/users')
@admin_required
def users():
    """Foydalanuvchilar ro'yxati"""
    user = User.query.get(session['user_id'])

    page = request.args.get('page', 1, type=int)
    per_page = 50

    users_query = User.query.order_by(User.created_at.desc())
    pagination = users_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin/users.html',
                         user=user,
                         users=pagination.items,
                         pagination=pagination)


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

    return render_template('admin/payments.html',
                         user=user,
                         payments=pagination.items,
                         pagination=pagination,
                         status_filter=status_filter)


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

    return render_template('admin/statistics.html',
                         user=user,
                         stats=stats,
                         region_stats=region_stats)
