from flask import Blueprint, render_template, request, session, jsonify, current_app
from models import User, UserTariff, PaymentRequest, Setting
from database import db
from routes.auth import login_required
from config import Config
from telegram_bot import send_payment_receipt_to_admin
import io


def _tariff_price(key, default):
    val = Setting.get(key) if Setting else None
    if val is not None and val != '':
        try:
            return int(val)
        except ValueError:
            pass
    return getattr(Config, key, default)


tariff_bp = Blueprint('tariff', __name__, url_prefix='/tariff')


@tariff_bp.route('/purchase')
@login_required
def purchase():
    """Tarif sotib olish sahifasi"""
    user = User.query.get(session['user_id'])
    bot_username = getattr(Config, 'TELEGRAM_BOT_USERNAME', 'nikoh_bot')
    
    # Obuna ma'lumotlarini olish
    active_tariff = None
    if user.has_active_tariff:
        active_tariff = user.active_tariff
    
    return render_template('tariff/purchase.html', 
                         user=user, 
                         bot_username=bot_username,
                         card_number=Config.PAYMENT_CARD_NUMBER,
                         card_name=Config.PAYMENT_CARD_NAME,
                         active_tariff=active_tariff)


@tariff_bp.route('/api/payment-info')
@login_required
def payment_info():
    """To'lov karta ma'lumotlari (SPA uchun)"""
    return jsonify({
        'card_number': Config.PAYMENT_CARD_NUMBER,
        'card_name': Config.PAYMENT_CARD_NAME
    })


def _tariff_status_dict(user):
    """Foydalanuvchi tarif holati (get_status va page-data uchun umumiy)."""
    from datetime import datetime
    now = datetime.utcnow()
    resp = {'has_active_tariff': False, 'tariff': None, 'active_top': None}

    active_top_tariff = UserTariff.query.filter(
        UserTariff.user_id == user.id,
        UserTariff.is_active == True,
        UserTariff.expires_at > now,
        UserTariff.is_top == True,
        UserTariff.top_expires_at > now
    ).order_by(UserTariff.top_expires_at.desc()).first()

    if active_top_tariff:
        resp['active_top'] = {
            'is_active': True,
            'top_days_remaining': getattr(active_top_tariff, 'top_days_remaining', 0),
            'tariff_name': active_top_tariff.tariff_name
        }

    if not user.has_active_tariff:
        return resp

    active_tariff = user.active_tariff
    is_top_active = active_tariff.is_top and not active_tariff.is_top_expired
    resp['has_active_tariff'] = True
    resp['tariff'] = {
        'name': active_tariff.tariff_name,
        'requests_count': active_tariff.requests_count,
        'total_requests': active_tariff.total_requests,
        'is_top': is_top_active,
        'days_remaining': active_tariff.days_remaining,
        'top_days_remaining': getattr(active_tariff, 'top_days_remaining', 0) if is_top_active else 0,
        'expires_at': active_tariff.expires_at.isoformat() if active_tariff.expires_at else None
    }
    return resp


@tariff_bp.route('/api/status')
@login_required
def get_status():
    """Foydalanuvchining tarif holatini olish"""
    user = User.query.get(session['user_id'])
    return jsonify(_tariff_status_dict(user))


def _tariffs_catalog_list():
    """Sotib olinadigan tariflar ro'yxati (SPA)."""
    return [
        {
            'name': 'KUMUSH',
            'price': _tariff_price('KUMUSH_TARIFF_PRICE', getattr(Config, 'KUMUSH_TARIFF_PRICE', 50000)),
            'requests': Config.KUMUSH_TARIFF_REQUESTS,
            'days': Config.KUMUSH_TARIFF_DAYS,
            'top_days': Config.KUMUSH_TARIFF_TOP_DAYS,
            'features': ['Cheksiz ko\'rishlar', 'Asosiy filterlar', 'Silver badge']
        },
        {
            'name': 'OLTIN',
            'price': _tariff_price('OLTIN_TARIFF_PRICE', getattr(Config, 'OLTIN_TARIFF_PRICE', 100000)),
            'requests': Config.OLTIN_TARIFF_REQUESTS,
            'days': Config.OLTIN_TARIFF_DAYS,
            'top_days': Config.OLTIN_TARIFF_TOP_DAYS,
            'features': ['Cheksiz ko\'rishlar', 'Poiskda yuqorida turish', 'Gold badge']
        },
        {
            'name': 'VIP',
            'price': _tariff_price('VIP_TARIFF_PRICE', getattr(Config, 'VIP_TARIFF_PRICE', 250000)),
            'requests': Config.VIP_TARIFF_REQUESTS,
            'days': Config.VIP_TARIFF_DAYS,
            'top_days': Config.VIP_TARIFF_TOP_DAYS,
            'features': ['Cheksiz ko\'rishlar', 'Poiskda yuqorida turish', 'VIP badge (Special)', 'Shaxsiy menejer 24/7']
        }
    ]


@tariff_bp.route('/api/page-data')
@login_required
def get_tariff_page_data():
    """Tariflar sahifasi: status + katalog + karta — bitta so'rov (tezroq)."""
    user = User.query.get(session['user_id'])
    body = _tariff_status_dict(user)
    body['tariffs'] = _tariffs_catalog_list()
    body['payment_info'] = {
        'card_number': Config.PAYMENT_CARD_NUMBER,
        'card_name': Config.PAYMENT_CARD_NAME
    }
    r = jsonify(body)
    r.headers['Cache-Control'] = 'private, no-store'
    return r


@tariff_bp.route('/my-tariffs')
@login_required
def my_tariffs():
    """Mening tariflarim"""
    user = User.query.get(session['user_id'])

    # Barcha tariflar (aktiv va o'tgan)
    tariffs = UserTariff.query.filter_by(user_id=user.id).order_by(
        UserTariff.created_at.desc()
    ).all()

    return render_template('tariff/my_tariffs.html',
                         user=user,
                         tariffs=tariffs)


@tariff_bp.route('/api/create-payment-request', methods=['POST'])
@login_required
def create_payment_request():
    """To'lov so'rovini yaratish va rasmni yuborish"""
    user = User.query.get(session['user_id'])
    
    # Form data yoki JSON tekshirish
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Form data (rasm bilan)
        tariff_name = request.form.get('tariff_name')
        amount = int(request.form.get('amount'))
        message = request.form.get('message', '')
        receipt_image = request.files.get('receipt_image')
    else:
        # JSON (eski usul - Telegram bot uchun)
        data = request.get_json()
        tariff_name = data.get('tariff_name')
        amount = data.get('amount')
        message = data.get('message', '')
        receipt_image = None
    
    if not tariff_name or not amount:
        return jsonify({'error': 'Tarif nomi va summa kerak'}), 400
    
    if not receipt_image and request.content_type and 'multipart/form-data' in request.content_type:
        return jsonify({'error': 'To\'lov cheki rasmi kerak'}), 400
    
    # To'lov so'rovini yaratish
    payment_request = PaymentRequest(
        user_id=user.id,
        tariff_name=tariff_name,
        amount=amount,
        receipt_message=message,
        status='pending'
    )
    db.session.add(payment_request)
    db.session.commit()
    
    # Agar rasm bo'lsa, adminga yuborish (background thread'da) — barcha tariflar (KUMUSH, OLTIN, VIP, TOP_*)
    if receipt_image:
        try:
            image_data = receipt_image.read()
            image_filename = receipt_image.filename or 'receipt.jpg'
            if not image_data or len(image_data) == 0:
                import logging
                logging.warning("create_payment_request: receipt_image bo'sh, adminga yuborilmaydi (tariff=%s)", tariff_name)
            else:
                import threading
                flask_app = current_app._get_current_object()
                thread = threading.Thread(
                    target=send_payment_receipt_to_admin,
                    args=(payment_request.id, image_data, image_filename, flask_app),
                    daemon=True
                )
                thread.start()
        except Exception as e:
            import traceback
            import logging
            logging.error("create_payment_request: adminga chek yuborishda xatolik (tariff=%s): %s", tariff_name, e)
            traceback.print_exc()
    
    return jsonify({
        'success': True,
        'message': 'To\'lov so\'rovi yaratildi va adminga yuborildi',
        'payment_request_id': payment_request.id
    })


@tariff_bp.route('/api/tariffs')
@login_required
def get_tariffs():
    """Barcha tariflar ro'yxatini olish"""
    return jsonify({'tariffs': _tariffs_catalog_list()})


@tariff_bp.route('/payment-instructions')
@login_required
def payment_instructions():
    """To'lov yo'riqnomasi"""
    user = User.query.get(session['user_id'])

    tariff_info = {
        'name': 'KUMUSH',
        'price': Config.KUMUSH_TARIFF_PRICE,
        'card_number': Config.PAYMENT_CARD_NUMBER,
        'card_name': Config.PAYMENT_CARD_NAME
    }

    return render_template('tariff/payment_instructions.html',
                         user=user,
                         tariff=tariff_info)
