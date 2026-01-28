from flask import Blueprint, render_template, request, session, jsonify, current_app
from models import User, UserTariff, PaymentRequest
from database import db
from routes.auth import login_required
from config import Config
from telegram_bot import send_payment_receipt_to_admin
import io

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


@tariff_bp.route('/api/status')
@login_required
def get_status():
    """Foydalanuvchining tarif holatini olish"""
    user = User.query.get(session['user_id'])

    if not user.has_active_tariff:
        return jsonify({
            'has_active_tariff': False,
            'tariff': None
        })

    active_tariff = user.active_tariff

    return jsonify({
        'has_active_tariff': True,
        'tariff': {
            'name': active_tariff.tariff_name,
            'requests_count': active_tariff.requests_count,
            'total_requests': active_tariff.total_requests,
            'is_top': active_tariff.is_top and not active_tariff.is_top_expired,
            'days_remaining': active_tariff.days_remaining,
            'expires_at': active_tariff.expires_at.isoformat() if active_tariff.expires_at else None
        }
    })


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
    
    # Agar rasm bo'lsa, adminga yuborish (background thread'da)
    if receipt_image:
        try:
            # Rasmni o'qish
            image_data = receipt_image.read()
            image_filename = receipt_image.filename
            
            # Background thread'da yuborish (tez ishlashi uchun)
            import threading
            flask_app = current_app._get_current_object()
            thread = threading.Thread(
                target=send_payment_receipt_to_admin,
                args=(payment_request.id, image_data, image_filename, flask_app),
                daemon=True
            )
            thread.start()
            
            # Rasmni saqlash (ixtiyoriy - file_id Telegram'da saqlanadi)
            # payment_request.receipt_file_id = file_id  # Telegram'dan qaytgan file_id
            db.session.commit()
        except Exception as e:
            import traceback
            print(f"Error sending receipt to admin: {e}")
            traceback.print_exc()
            # Xatolik bo'lsa ham payment_request yaratilgan bo'ladi
    
    return jsonify({
        'success': True,
        'message': 'To\'lov so\'rovi yaratildi va adminga yuborildi',
        'payment_request_id': payment_request.id
    })


@tariff_bp.route('/api/tariffs')
@login_required
def get_tariffs():
    """Barcha tariflar ro'yxatini olish"""
    tariffs = [
        {
            'name': 'KUMUSH',
            'price': Config.KUMUSH_TARIFF_PRICE,
            'requests': Config.KUMUSH_TARIFF_REQUESTS,
            'days': Config.KUMUSH_TARIFF_DAYS,
            'top_days': Config.KUMUSH_TARIFF_TOP_DAYS,
            'features': ['Cheksiz ko\'rishlar', 'Asosiy filterlar', 'Silver badge']
        },
        {
            'name': 'OLTIN',
            'price': Config.OLTIN_TARIFF_PRICE,
            'requests': Config.OLTIN_TARIFF_REQUESTS,
            'days': Config.OLTIN_TARIFF_DAYS,
            'top_days': Config.OLTIN_TARIFF_TOP_DAYS,
            'features': ['Cheksiz ko\'rishlar', 'Poiskda yuqorida turish', 'Gold badge']
        },
        {
            'name': 'VIP',
            'price': Config.VIP_TARIFF_PRICE,
            'requests': Config.VIP_TARIFF_REQUESTS,
            'days': Config.VIP_TARIFF_DAYS,
            'top_days': Config.VIP_TARIFF_TOP_DAYS,
            'features': ['Cheksiz ko\'rishlar', 'Poiskda yuqorida turish', 'VIP badge (Special)', 'Shaxsiy menejer 24/7']
        }
    ]
    
    return jsonify({'tariffs': tariffs})


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
