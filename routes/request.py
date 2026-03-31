from flask import Blueprint, render_template, request, session, jsonify, current_app
from models import User, MatchRequest
from database import db
from routes.auth import login_required, profile_required
from telegram_bot import send_notification, send_notification_sync
from sqlalchemy import or_, and_
from sqlalchemy.orm import selectinload
from datetime import datetime
import asyncio

request_bp = Blueprint('request', __name__, url_prefix='/requests')


def _match_requests_json(rows):
    """Bir nechta so'rovni JSON qilish — bitta batch so'rov, yengil to_card_dict."""
    if not rows:
        return []
    from models.profile import Profile
    from models.tariff import UserTariff

    user_ids = set()
    profile_ids = set()
    for r in rows:
        user_ids.add(r.sender_id)
        user_ids.add(r.receiver_id)
        if r.receiver_profile_id:
            profile_ids.add(r.receiver_profile_id)

    prof_filter = Profile.user_id.in_(user_ids)
    if profile_ids:
        prof_filter = db.or_(prof_filter, Profile.id.in_(profile_ids))
    profiles = Profile.query.filter(prof_filter).all()

    by_id = {p.id: p for p in profiles}
    by_user = {}
    for p in profiles:
        by_user.setdefault(p.user_id, []).append(p)

    def pick_primary(uid):
        ps = by_user.get(uid, [])
        if not ps:
            return None
        prim = [x for x in ps if getattr(x, 'is_primary', False)]
        pool = prim if prim else ps
        return min(pool, key=lambda x: x.id)

    now = datetime.utcnow()
    tariffs = UserTariff.query.filter(
        UserTariff.user_id.in_(user_ids),
        UserTariff.is_active == True,
        UserTariff.expires_at > now
    ).all()
    tariff_rc = {}
    for t in tariffs:
        if t.user_id not in tariff_rc:
            tariff_rc[t.user_id] = t.requests_count

    def card(p, uid):
        if not p:
            return None
        d = p.to_card_dict()
        d['user_id'] = uid
        d['requests_count'] = tariff_rc.get(uid, 0)
        return d

    out = []
    for r in rows:
        sender_p = pick_primary(r.sender_id)
        recv_p = by_id.get(r.receiver_profile_id) or pick_primary(r.receiver_id)
        chat_data = None
        if r.chat:
            chat_data = {
                'id': r.chat.id,
                'is_active': r.chat.is_active,
                'is_expired': r.chat.is_expired,
                'days_remaining': r.chat.days_remaining
            }
        out.append({
            'id': r.id,
            'sender': card(sender_p, r.sender_id),
            'receiver': card(recv_p, r.receiver_id),
            'message': r.message,
            'status': r.status,
            'created_at': r.created_at.isoformat() if r.created_at else None,
            'responded_at': r.responded_at.isoformat() if r.responded_at else None,
            'chat': chat_data
        })
    return out


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

    sent_requests = MatchRequest.query.options(
        selectinload(MatchRequest.chat)
    ).filter_by(
        sender_id=current_user.id
    ).order_by(MatchRequest.created_at.desc()).all()

    requests_data = _match_requests_json(sent_requests)

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
    received_requests = MatchRequest.query.options(
        selectinload(MatchRequest.chat)
    ).filter(
        MatchRequest.receiver_id == current_user.id,
        MatchRequest.status == 'pending'
    ).order_by(MatchRequest.created_at.desc()).all()

    requests_data = _match_requests_json(received_requests)

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
    accepted_requests = MatchRequest.query.options(
        selectinload(MatchRequest.chat)
    ).filter(
        db.or_(
            db.and_(MatchRequest.sender_id == current_user.id, MatchRequest.status == 'accepted'),
            db.and_(MatchRequest.receiver_id == current_user.id, MatchRequest.status == 'accepted')
        )
    ).order_by(MatchRequest.responded_at.desc()).all()

    requests_data = _match_requests_json(accepted_requests)

    return jsonify({
        'requests': requests_data,
        'count': len(requests_data)
    })


@request_bp.route('/api/send', methods=['POST'])
@profile_required
def send_request():
    """So'rov yuborish"""
    try:
        current_user = User.query.get(session['user_id'])
        if not current_user:
            return jsonify({'error': 'Foydalanuvchi topilmadi'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Ma\'lumotlar topilmadi'}), 400

        receiver_id = data.get('receiver_id')
        receiver_profile_id = data.get('receiver_profile_id')
        message = data.get('message', '')

        if not receiver_id:
            return jsonify({'error': 'receiver_id kerak'}), 400

        # O'ziga yubormasligi
        if receiver_id == current_user.id:
            return jsonify({'error': 'O\'zingizga so\'rov yubora olmaysiz'}), 400

        # Qabul qiluvchi mavjudligini tekshirish
        receiver = User.query.get(receiver_id)
        if not receiver:
            return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404
        
        # Qaysi profil (e'lon) uchun: receiver_profile_id berilsa shu profil, aks holda asosiy profil
        from models import Profile
        target_profile = Profile.query.get(receiver_profile_id) if receiver_profile_id else receiver.profile
        if not target_profile or target_profile.user_id != int(receiver_id) or not target_profile.is_active:
            return jsonify({'error': 'E\'lon topilmadi yoki aktiv emas'}), 404

        # Tarif va so'rovlar sonini tekshirish
        if not current_user.has_active_tariff:
            return jsonify({'error': 'Tarif kerak. Iltimos, tarif sotib oling.'}), 400

        active_tariff = current_user.active_tariff
        if not active_tariff:
            return jsonify({'error': 'Tarif topilmadi. Iltimos, tarif sotib oling.'}), 400
        
        if active_tariff.requests_count <= 0:
            return jsonify({'error': 'So\'rovlar tugagan. Yangi tarif sotib oling.'}), 400

        # Allaqachon so'rov yuborilganmi? (xuddi shu e'lon uchun)
        profile_filter = (MatchRequest.receiver_profile_id == target_profile.id) if target_profile.id else MatchRequest.receiver_profile_id.is_(None)
        existing_request = MatchRequest.query.filter(
            MatchRequest.sender_id == current_user.id,
            MatchRequest.receiver_id == receiver_id,
            profile_filter
        ).first()
        if not existing_request:
            existing_request = MatchRequest.query.filter(
                MatchRequest.sender_id == receiver_id,
                MatchRequest.receiver_id == current_user.id,
                profile_filter
            ).first()

        if existing_request:
            if existing_request.status == 'accepted' and existing_request.chat:
                return jsonify({'error': 'Chat allaqachon mavjud', 'chat_id': existing_request.chat.id}), 400
            return jsonify({'error': 'Allaqachon so\'rov yuborgan'}), 400

        # So'rov yaratish (qaysi e'lon uchun ekanini saqlash)
        new_request = MatchRequest(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            receiver_profile_id=target_profile.id,
            message=message
        )
        db.session.add(new_request)

        # Tarifdan so'rov ayirish (use_request() o'zi commit qiladi)
        if not active_tariff.use_request():
            db.session.rollback()
            return jsonify({'error': 'So\'rovlar tugagan. Yangi tarif sotib oling.'}), 400
        
        # use_request() o'zi commit qiladi, lekin new_request ham commit qilish kerak
        # Shuning uchun yana commit qilamiz (agar use_request() commit qilmasa)
        try:
            db.session.commit()
        except Exception as commit_err:
            # Agar commit xatolik bersa, rollback va xatolik qaytarish
            db.session.rollback()
            import logging
            import traceback
            logging.error(f"Error committing request: {commit_err}")
            traceback.print_exc()
            return jsonify({'error': 'So\'rov saqlashda xatolik', 'message': 'Qaytadan urinib ko\'ring.'}), 500

        # Qabul qiluvchiga va yuboruvchiga bot orqali xabar
        def send_notifications():
            try:
                sender_name = (current_user.profile and current_user.profile.name) or 'Foydalanuvchi'
                receiver_name = (receiver.profile and receiver.profile.name) or 'Foydalanuvchi'

                # Qabul qiluvchiga: yangi so'rov keldi
                receiver_message = f"""💌 Yangi so'rov keldi!

{sender_name} sizga tanishuv so'rovi yubordi.

📱 So'rovlarni ko'rish va javob berish uchun Mini App'ni oching."""
                if receiver.telegram_id:
                    send_notification_sync(receiver.telegram_id, receiver_message)

                # Yuboruvchiga: so'rov yuborildi
                sender_message = f"""✅ So'rov yuborildi!

{receiver_name} ga so'rovingiz yuborildi. Javobini kuting.

📱 Mini App'da ko'rish: /start"""
                if current_user.telegram_id:
                    send_notification_sync(current_user.telegram_id, sender_message)
            except Exception as e:
                import logging
                logging.error(f"Error sending request notifications: {e}")

        # Background threadda xabarlarni yuborish
        import threading
        thread = threading.Thread(target=send_notifications)
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'message': 'So\'rov yuborildi',
            'request': _match_requests_json([new_request])[0]
        })
    except Exception as e:
        db.session.rollback()
        import logging
        import traceback
        logging.error(f"Unexpected error in send_request: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Xatolik yuz berdi', 'message': 'Qaytadan urinib ko\'ring.'}), 500


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
            sender_name = sender.profile.name if sender.profile else 'Foydalanuvchi'
            receiver_name = receiver.profile.name if receiver.profile else 'Foydalanuvchi'
            
            # Yuboruvchiga xabar (so'rov qabul qilindi)
            sender_message = f"""
✅ So'rovingiz qabul qilindi!

{receiver_name} so'rovingizni qabul qildi.

💬 7 kunlik chat ochildi! Endi xabarlashishingiz mumkin.

📱 Mini App'da chatga kirish: /start
"""
            # Qabul qiluvchiga xabar (chat ochildi)
            receiver_message = f"""
💬 Chat ochildi!

{sender_name} bilan 7 kunlik chat ochildi.

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
            receiver_name = current_user.profile.name if current_user.profile else 'Foydalanuvchi'
            
            sender_message = f"""
❌ So'rovingiz rad etildi

{receiver_name} so'rovingizni rad etdi.

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
