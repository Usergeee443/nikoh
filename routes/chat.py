from flask import Blueprint, render_template, request, session, jsonify
from models import User, Chat, Message
from models.profile import Profile
from database import db
from routes.auth import login_required, profile_required, basic_profile_required
from datetime import datetime
from sqlalchemy import func
from telegram_bot import send_notification
import asyncio
import threading

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


def _commit_expired_chats(chats):
    """Muddati o'tgan chatlarni bitta commit bilan o'chirish (har chat uchun commit emas)."""
    changed = False
    now = datetime.utcnow()
    for c in chats:
        if c.expires_at and now > c.expires_at and c.is_active:
            c.is_active = False
            changed = True
    if changed:
        db.session.commit()


def _serialize_chat_row(chat, current_user, users_by_id, primary_profile_by_user, last_msg_by_id, unread_by_id):
    other_user_id = chat.get_other_user_id(current_user.id)
    other_user = users_by_id.get(other_user_id)
    prof = primary_profile_by_user.get(other_user_id)
    last_message = last_msg_by_id.get(chat.id)
    unread_count = unread_by_id.get(chat.id, 0)

    other_name = 'Foydalanuvchi'
    other_age = None
    if prof:
        other_name = prof.name or other_name
        other_age = prof.age

    return {
        'id': chat.id,
        'profile_id': chat.get_my_profile_id(current_user.id) if hasattr(chat, 'get_my_profile_id') else None,
        'other_user': {
            'id': other_user.id if other_user else other_user_id,
            'name': other_name,
            'age': other_age,
            'user_id': other_user_id,
            'region': getattr(prof, 'region', None) if prof else None,
            'location': getattr(prof, 'region', None) if prof else None,
        },
        'last_message': {
            'id': last_message.id,
            'content': last_message.content if last_message else None,
            'created_at': last_message.created_at.isoformat() if last_message else None,
            'is_mine': last_message.sender_id == current_user.id if last_message else False,
            'sender_id': last_message.sender_id if last_message else None
        } if last_message else None,
        'unread_count': unread_count,
        'is_active': chat.is_active,
        'is_expired': chat.is_expired,
        'days_remaining': chat.days_remaining,
        'hours_remaining': chat.hours_remaining,
        'expires_at': chat.expires_at.isoformat() if chat.expires_at else None
    }


def _build_chat_list_payload(chats, current_user):
    if not chats:
        return []
    chat_ids = [c.id for c in chats]
    uid = current_user.id
    other_ids = list({(c.user2_id if c.user1_id == uid else c.user1_id) for c in chats})

    users_by_id = {u.id: u for u in User.query.filter(User.id.in_(other_ids)).all()}

    profiles = Profile.query.filter(Profile.user_id.in_(other_ids)).all()
    primary_profile_by_user = {}
    for p in profiles:
        ou = p.user_id
        if ou not in primary_profile_by_user:
            primary_profile_by_user[ou] = p
        if getattr(p, 'is_primary', False):
            primary_profile_by_user[ou] = p

    msg_sub = db.session.query(
        Message.chat_id,
        func.max(Message.id).label('max_id')
    ).filter(Message.chat_id.in_(chat_ids)).group_by(Message.chat_id).subquery()

    last_msgs = db.session.query(Message).join(
        msg_sub, Message.id == msg_sub.c.max_id
    ).all()
    last_msg_by_id = {m.chat_id: m for m in last_msgs}

    unread_rows = db.session.query(
        Message.chat_id,
        func.count(Message.id)
    ).filter(
        Message.chat_id.in_(chat_ids),
        Message.sender_id != current_user.id,
        Message.is_read == False
    ).group_by(Message.chat_id).all()
    unread_by_id = {cid: cnt for cid, cnt in unread_rows}

    return [
        _serialize_chat_row(c, current_user, users_by_id, primary_profile_by_user, last_msg_by_id, unread_by_id)
        for c in chats
    ]


@chat_bp.route('/')
@basic_profile_required
def index():
    """Chatlar ro'yxati - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])
    return render_template('spa.html', user=user)


@chat_bp.route('/api/list')
@basic_profile_required
def get_chats():
    """Foydalanuvchining chatlarini olish (profile_id bo'lsa shu e'lon uchun)"""
    current_user = User.query.get(session['user_id'])
    profile_id = request.args.get('profile_id', type=int)

    chats = current_user.get_chats()
    _commit_expired_chats(chats)
    now = datetime.utcnow()

    # Bir nechta e'lon bo'lsa: faqat shu profil uchun chatlarni filtrlash
    if profile_id is not None:
        chats = [c for c in chats if c.get_my_profile_id(current_user.id) == profile_id]

    active_chats = [c for c in chats if c.expires_at and now <= c.expires_at]
    archive_chats = [c for c in chats if c.expires_at and now > c.expires_at]

    # Mening e'lonlarim (ism bo'yicha filtrlash uchun tepada tablar)
    my_profiles = [{'id': p.id, 'name': p.name or 'E\'lon'} for p in current_user.profiles.order_by('id').all()]

    chats_data = _build_chat_list_payload(active_chats, current_user)
    archive_data = _build_chat_list_payload(archive_chats, current_user)

    return jsonify({
        'chats': chats_data,
        'chats_archive': archive_data,
        'count': len(chats_data),
        'archive_count': len(archive_data),
        'my_profiles': my_profiles
    })


@chat_bp.route('/<int:chat_id>')
@basic_profile_required
def view_chat(chat_id):
    """Chatni ko'rish - SPA ga yo'naltirish"""
    current_user = User.query.get(session['user_id'])

    chat = Chat.query.get(chat_id)

    if not chat:
        return render_template('error.html', message='Chat topilmadi'), 404

    # Foydalanuvchi chatga kirish huquqiga ega ekanligini tekshirish
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        return render_template('error.html', message='Sizda bu chatga kirish huquqi yo\'q'), 403

    # Holatni yangilash
    chat.check_and_update_status()

    # SPA ga yo'naltirish
    return render_template('spa.html', user=current_user)


@chat_bp.route('/api/<int:chat_id>/messages')
@basic_profile_required
def get_messages(chat_id):
    """Chat xabarlarini olish"""
    current_user = User.query.get(session['user_id'])

    chat = Chat.query.get(chat_id)

    if not chat:
        return jsonify({'error': 'Chat topilmadi'}), 404

    # Kirish huquqini tekshirish
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        return jsonify({'error': 'Sizda bu chatga kirish huquqi yo\'q'}), 403

    chat.check_and_update_status()

    # Saralash: desc = yangi birinchi (default), asc = eski birinchi
    sort_order = request.args.get('sort', 'desc', type=str)
    if sort_order not in ('asc', 'desc'):
        sort_order = 'desc'
    messages = chat.get_messages(limit=500, sort=sort_order)

    # O'qilmagan xabarlarni bitta commit bilan belgilash (har xabar uchun commit sekin)
    to_mark = [m for m in messages if m.sender_id != current_user.id and not m.is_read]
    for m in to_mark:
        m.is_read = True
    if to_mark:
        db.session.commit()

    messages_data = [msg.to_dict() for msg in messages]

    # Chat ma'lumotlarini qo'shish
    other_user_id = chat.get_other_user_id(current_user.id)
    other_user = User.query.get(other_user_id)

    return jsonify({
        'messages': messages_data,
        'chat': {
            'id': chat.id,
            'is_active': chat.is_active,
            'is_expired': chat.is_expired,
            'days_remaining': chat.days_remaining,
            'hours_remaining': chat.hours_remaining,
            'expires_at': chat.expires_at.isoformat() if chat.expires_at else None,
            'other_user': {
                'id': other_user.id,
                'name': other_user.profile.name if other_user.profile else 'Foydalanuvchi'
            }
        }
    })


@chat_bp.route('/api/<int:chat_id>/send', methods=['POST'])
@basic_profile_required
def send_message(chat_id):
    """Xabar yuborish"""
    current_user = User.query.get(session['user_id'])
    data = request.get_json()

    chat = Chat.query.get(chat_id)

    if not chat:
        return jsonify({'error': 'Chat topilmadi'}), 404

    # Kirish huquqini tekshirish
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        return jsonify({'error': 'Sizda bu chatga kirish huquqi yo\'q'}), 403

    # Chat aktiv ekanligini tekshirish
    chat.check_and_update_status()

    if not chat.is_active or chat.is_expired:
        return jsonify({'error': 'Chat muddati tugagan'}), 400

    content = data.get('content')

    if not content or not content.strip():
        return jsonify({'error': 'Xabar bo\'sh bo\'lishi mumkin emas'}), 400

    # Xabar yaratish
    message = Message(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=content.strip()
    )
    db.session.add(message)
    db.session.commit()

    # Qabul qiluvchiga bildirishnoma
    other_user_id = chat.get_other_user_id(current_user.id)
    other_user = User.query.get(other_user_id)
    
    def send_notification_to_receiver():
        try:
            sender_name = current_user.profile.name if current_user.profile else 'Foydalanuvchi'
            message_preview = content.strip()[:100] + ('...' if len(content.strip()) > 100 else '')
            
            notification_message = f"""
💬 Yangi xabar!

{sender_name} sizga xabar yubordi:

"{message_preview}"

📱 Mini App'da ko'rish: /start
"""
            
            # Asinxron xabarni yuborish
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if other_user.telegram_id:
                loop.run_until_complete(send_notification(other_user.telegram_id, notification_message))
            
            loop.close()
        except Exception as e:
            import logging
            logging.error(f"Error sending notification: {e}")

    # Background threadda xabarni yuborish
    thread = threading.Thread(target=send_notification_to_receiver)
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'message': message.to_dict()
    })


@chat_bp.route('/api/<int:chat_id>/mark-read', methods=['POST'])
@basic_profile_required
def mark_messages_read(chat_id):
    """Xabarlarni o'qilgan deb belgilash"""
    current_user = User.query.get(session['user_id'])

    chat = Chat.query.get(chat_id)

    if not chat:
        return jsonify({'error': 'Chat topilmadi'}), 404

    # Kirish huquqini tekshirish
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        return jsonify({'error': 'Sizda bu chatga kirish huquqi yo\'q'}), 403

    # O'qilmagan xabarlarni o'qilgan deb belgilash
    unread_messages = chat.messages.filter(
        Message.sender_id != current_user.id,
        Message.is_read == False
    ).all()

    for message in unread_messages:
        message.is_read = True
    if unread_messages:
        db.session.commit()

    return jsonify({
        'success': True,
        'marked_count': len(unread_messages)
    })
