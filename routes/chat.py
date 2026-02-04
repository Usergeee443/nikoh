from flask import Blueprint, render_template, request, session, jsonify
from models import User, Chat, Message
from database import db
from routes.auth import login_required, profile_required, basic_profile_required
from datetime import datetime
from telegram_bot import send_notification
import asyncio
import threading

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


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
    # Bir nechta e'lon bo'lsa: faqat shu profil uchun chatlarni filtrlash
    if profile_id is not None:
        chats = [c for c in chats if c.get_my_profile_id(current_user.id) == profile_id]

    # Mening e'lonlarim (ism bo'yicha filtrlash uchun tepada tablar)
    my_profiles = [{'id': p.id, 'name': p.name or 'E\'lon'} for p in current_user.profiles.order_by('id').all()]

    chats_data = []
    for chat in chats:
        # Holatni yangilash
        chat.check_and_update_status()

        # Boshqa foydalanuvchi
        other_user_id = chat.get_other_user_id(current_user.id)
        other_user = User.query.get(other_user_id)

        # Oxirgi xabar
        last_message = chat.messages.order_by(Message.created_at.desc()).first()

        # O'qilmagan xabarlar soni
        unread_count = chat.messages.filter(
            Message.sender_id != current_user.id,
            Message.is_read == False
        ).count()

        my_profile_id = chat.get_my_profile_id(current_user.id) if hasattr(chat, 'get_my_profile_id') else None
        chat_data = {
            'id': chat.id,
            'profile_id': my_profile_id,
            'other_user': {
                'id': other_user.id,
                'name': other_user.profile.name if other_user.profile else 'Foydalanuvchi',
                'age': other_user.profile.age if other_user.profile else None
            },
            'last_message': {
                'content': last_message.content if last_message else None,
                'created_at': last_message.created_at.isoformat() if last_message else None,
                'is_mine': last_message.sender_id == current_user.id if last_message else False
            } if last_message else None,
            'unread_count': unread_count,
            'is_active': chat.is_active,
            'is_expired': chat.is_expired,
            'days_remaining': chat.days_remaining,
            'hours_remaining': chat.hours_remaining,
            'expires_at': chat.expires_at.isoformat() if chat.expires_at else None
        }

        chats_data.append(chat_data)

    return jsonify({
        'chats': chats_data,
        'count': len(chats_data),
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

    # Saralash: desc = yangi birinchi (default), asc = eski birinchi
    sort_order = request.args.get('sort', 'desc', type=str)
    if sort_order not in ('asc', 'desc'):
        sort_order = 'desc'
    messages = chat.get_messages(limit=1000, sort=sort_order)

    # O'qilmagan xabarlarni o'qilgan deb belgilash
    for message in messages:
        if message.sender_id != current_user.id and not message.is_read:
            message.mark_as_read()

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
            notification_message = f"""
💬 Yangi xabar!

{current_user.profile.name if current_user.profile else 'Foydalanuvchi'} sizga xabar yubordi.

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
        message.mark_as_read()

    return jsonify({
        'success': True,
        'marked_count': len(unread_messages)
    })
