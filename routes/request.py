from flask import Blueprint, render_template, request, session, jsonify, current_app
from models import User, MatchRequest
from database import db
from routes.auth import login_required, profile_required
from telegram_bot import send_notification
from sqlalchemy import or_, and_
import asyncio

request_bp = Blueprint('request', __name__, url_prefix='/requests')


@request_bp.route('/')
@profile_required
def index():
    """So'rovlar sahifasi - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])
    return render_template('spa.html', user=user)


@request_bp.route('/api/sent')
@profile_required
def get_sent_requests():
    """Yuborilgan so'rovlar (barcha statuslar)"""
    current_user = User.query.get(session['user_id'])

    sent_requests = MatchRequest.query.filter_by(
        sender_id=current_user.id
    ).order_by(MatchRequest.created_at.desc()).all()

    requests_data = [req.to_dict() for req in sent_requests]

    return jsonify({
        'requests': requests_data,
        'count': len(requests_data)
    })


@request_bp.route('/api/received')
@profile_required
def get_received_requests():
    """Qabul qilingan so'rovlar (faqat pending)"""
    current_user = User.query.get(session['user_id'])

    # Faqat pending so'rovlarni ko'rsatish (accepted so'rovlar "Chatlar" bo'limida)
    received_requests = MatchRequest.query.filter(
        MatchRequest.receiver_id == current_user.id,
        MatchRequest.status == 'pending'
    ).order_by(MatchRequest.created_at.desc()).all()

    requests_data = [req.to_dict() for req in received_requests]

    return jsonify({
        'requests': requests_data,
        'count': len(requests_data)
    })


@request_bp.route('/api/accepted')
@profile_required
def get_accepted_requests():
    """Qabul qilingan so'rovlar (chat bilan)"""
    current_user = User.query.get(session['user_id'])

    # Qabul qilingan so'rovlar (chat bilan)
    accepted_requests = MatchRequest.query.filter(
        db.or_(
            db.and_(MatchRequest.sender_id == current_user.id, MatchRequest.status == 'accepted'),
            db.and_(MatchRequest.receiver_id == current_user.id, MatchRequest.status == 'accepted')
        )
    ).order_by(MatchRequest.responded_at.desc()).all()

    requests_data = [req.to_dict() for req in accepted_requests]

    return jsonify({
        'requests': requests_data,
        'count': len(requests_data)
    })


@request_bp.route('/api/send', methods=['POST'])
@profile_required
def send_request():
    """So'rov yuborish"""
    current_user = User.query.get(session['user_id'])
    data = request.get_json()

    receiver_id = data.get('receiver_id')
    message = data.get('message', '')

    if not receiver_id:
        return jsonify({'error': 'receiver_id kerak'}), 400

    # O'ziga yubormasligi
    if receiver_id == current_user.id:
        return jsonify({'error': 'O\'zingizga so\'rov yubora olmaysiz'}), 400

    # Qabul qiluvchi mavjudligini tekshirish
    receiver = User.query.get(receiver_id)
    if not receiver or not receiver.profile or not receiver.profile.is_active:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    # Tarif va so'rovlar sonini tekshirish
    if not current_user.has_active_tariff:
        return jsonify({'error': 'Tarif kerak. Iltimos, tarif sotib oling.'}), 400

    active_tariff = current_user.active_tariff
    if active_tariff.requests_count <= 0:
        return jsonify({'error': 'So\'rovlar tugagan. Yangi tarif sotib oling.'}), 400

    # Allaqachon so'rov yuborilganmi? (ikki tomonlama tekshirish)
    existing_request = MatchRequest.query.filter(
        db.or_(
            db.and_(MatchRequest.sender_id == current_user.id, MatchRequest.receiver_id == receiver_id),
            db.and_(MatchRequest.sender_id == receiver_id, MatchRequest.receiver_id == current_user.id)
        )
    ).first()

    if existing_request:
        if existing_request.status == 'accepted' and existing_request.chat:
            return jsonify({'error': 'Chat allaqachon mavjud', 'chat_id': existing_request.chat.id}), 400
        return jsonify({'error': 'Allaqachon so\'rov yuborgan'}), 400

    # So'rov yaratish
    new_request = MatchRequest(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        message=message
    )
    db.session.add(new_request)

    # Tarifdan so'rov ayirish
    active_tariff.use_request()

    db.session.commit()

    # Qabul qiluvchiga bildirishnoma yuborish
    def send_notifications():
        try:
            # Qabul qiluvchiga xabar
            receiver_message = f"""
💌 Yangi so'rov!

{current_user.profile.name if current_user.profile else 'Foydalanuvchi'} sizga so'rov yubordi.

📱 Mini App'da ko'rish uchun: /start
"""
            # Yuboruvchiga xabar
            sender_message = f"""
✅ So'rov yuborildi!

{receiver.profile.name if receiver.profile else 'Foydalanuvchi'} ga so'rovingiz yuborildi.

📱 Mini App'da ko'rish uchun: /start
"""
            
            # Asinxron xabarlarni yuborish
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Qabul qiluvchiga
            if receiver.telegram_id:
                loop.run_until_complete(send_notification(receiver.telegram_id, receiver_message))
            
            # Yuboruvchiga
            if current_user.telegram_id:
                loop.run_until_complete(send_notification(current_user.telegram_id, sender_message))
            
            loop.close()
        except Exception as e:
            import logging
            logging.error(f"Error sending notifications: {e}")

    # Background threadda xabarlarni yuborish
    import threading
    thread = threading.Thread(target=send_notifications)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'So\'rov yuborildi',
        'request': new_request.to_dict()
    })


@request_bp.route('/api/<int:request_id>/accept', methods=['POST'])
@profile_required
def accept_request(request_id):
    """So'rovni qabul qilish"""
    current_user = User.query.get(session['user_id'])

    match_request = MatchRequest.query.get(request_id)

    if not match_request:
        return jsonify({'error': 'So\'rov topilmadi'}), 404

    # Qabul qiluvchi ekanligini tekshirish
    if match_request.receiver_id != current_user.id:
        return jsonify({'error': 'Bu so\'rovni qabul qila olmaysiz'}), 403

    # So'rov pending holatida ekanligini tekshirish
    if not match_request.is_pending:
        return jsonify({'error': 'Bu so\'rov allaqachon qayta ishlangan'}), 400

    # So'rovni qabul qilish va chat yaratish
    chat = match_request.accept()
    
    # Yuboruvchi va qabul qiluvchi ma'lumotlari
    sender = User.query.get(match_request.sender_id)
    receiver = current_user

    # Yuboruvchiga va qabul qiluvchiga bildirishnoma
    def send_notifications():
        try:
            # Yuboruvchiga xabar (so'rov qabul qilindi)
            sender_message = f"""
✅ So'rovingiz qabul qilindi!

{receiver.profile.name if receiver.profile else 'Foydalanuvchi'} so'rovingizni qabul qildi.

💬 7 kunlik chat ochildi! Endi xabarlashishingiz mumkin.

📱 Mini App'da chatga kirish: /start
"""
            # Qabul qiluvchiga xabar (chat ochildi)
            receiver_message = f"""
💬 Chat ochildi!

{sender.profile.name if sender.profile else 'Foydalanuvchi'} bilan 7 kunlik chat ochildi.

📱 Mini App'da chatga kirish: /start
"""
            
            # Asinxron xabarlarni yuborish
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Yuboruvchiga
            if sender.telegram_id:
                loop.run_until_complete(send_notification(sender.telegram_id, sender_message))
            
            # Qabul qiluvchiga
            if receiver.telegram_id:
                loop.run_until_complete(send_notification(receiver.telegram_id, receiver_message))
            
            loop.close()
        except Exception as e:
            import logging
            logging.error(f"Error sending notifications: {e}")

    # Background threadda xabarlarni yuborish
    import threading
    thread = threading.Thread(target=send_notifications)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'So\'rov qabul qilindi',
        'chat_id': chat.id
    })


@request_bp.route('/api/<int:request_id>/reject', methods=['POST'])
@profile_required
def reject_request(request_id):
    """So'rovni rad etish"""
    current_user = User.query.get(session['user_id'])

    match_request = MatchRequest.query.get(request_id)

    if not match_request:
        return jsonify({'error': 'So\'rov topilmadi'}), 404

    # Qabul qiluvchi ekanligini tekshirish
    if match_request.receiver_id != current_user.id:
        return jsonify({'error': 'Bu so\'rovni rad qila olmaysiz'}), 403

    # So'rov pending holatida ekanligini tekshirish
    if not match_request.is_pending:
        return jsonify({'error': 'Bu so\'rov allaqachon qayta ishlangan'}), 400

    # So'rovni rad etish
    match_request.reject()
    
    # Yuboruvchi ma'lumotlari
    sender = User.query.get(match_request.sender_id)

    # Yuboruvchiga bildirishnoma
    def send_notification_to_sender():
        try:
            sender_message = f"""
❌ So'rovingiz rad etildi

{current_user.profile.name if current_user.profile else 'Foydalanuvchi'} so'rovingizni rad etdi.

📱 Mini App'da ko'rish uchun: /start
"""
            
            # Asinxron xabarni yuborish
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if sender.telegram_id:
                loop.run_until_complete(send_notification(sender.telegram_id, sender_message))
            
            loop.close()
        except Exception as e:
            import logging
            logging.error(f"Error sending notification: {e}")

    # Background threadda xabarni yuborish
    import threading
    thread = threading.Thread(target=send_notification_to_sender)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': 'So\'rov rad etildi'
    })


@request_bp.route('/api/<int:request_id>/cancel', methods=['POST'])
@profile_required
def cancel_request(request_id):
    """So'rovni bekor qilish"""
    current_user = User.query.get(session['user_id'])

    match_request = MatchRequest.query.get(request_id)

    if not match_request:
        return jsonify({'error': 'So\'rov topilmadi'}), 404

    # Yuboruvchi ekanligini tekshirish
    if match_request.sender_id != current_user.id:
        return jsonify({'error': 'Bu so\'rovni bekor qila olmaysiz'}), 403

    # So'rovni bekor qilish
    if not match_request.cancel():
        return jsonify({'error': 'Faqat pending so\'rovlarni bekor qilish mumkin'}), 400

    return jsonify({
        'success': True,
        'message': 'So\'rov bekor qilindi'
    })
