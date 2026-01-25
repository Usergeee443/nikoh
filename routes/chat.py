from flask import Blueprint, render_template, request, session, jsonify
from models import User, Chat, Message
from database import db
from routes.auth import login_required, profile_required
from datetime import datetime

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/')
@profile_required
def index():
    """Chatlar ro'yxati - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])
    return render_template('spa.html', user=user)


@chat_bp.route('/api/list')
@profile_required
def get_chats():
    """Foydalanuvchining barcha chatlarini olish"""
    current_user = User.query.get(session['user_id'])

    chats = current_user.get_chats()

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

        chat_data = {
            'id': chat.id,
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
        'count': len(chats_data)
    })


@chat_bp.route('/<int:chat_id>')
@profile_required
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
@profile_required
def get_messages(chat_id):
    """Chat xabarlarini olish"""
    current_user = User.query.get(session['user_id'])

    chat = Chat.query.get(chat_id)

    if not chat:
        return jsonify({'error': 'Chat topilmadi'}), 404

    # Kirish huquqini tekshirish
    if chat.user1_id != current_user.id and chat.user2_id != current_user.id:
        return jsonify({'error': 'Sizda bu chatga kirish huquqi yo\'q'}), 403

    # Xabarlarni olish
    messages = chat.get_messages(limit=1000)

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
@profile_required
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
    # TODO: Telegram notification
    other_user_id = chat.get_other_user_id(current_user.id)
    other_user = User.query.get(other_user_id)

    return jsonify({
        'success': True,
        'message': message.to_dict()
    })


@chat_bp.route('/api/<int:chat_id>/mark-read', methods=['POST'])
@profile_required
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
