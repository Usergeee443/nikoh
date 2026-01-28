from flask import Blueprint, render_template, request, session, jsonify
from models import User, Favorite, Profile
from database import db
from routes.auth import login_required, profile_required

favorite_bp = Blueprint('favorite', __name__, url_prefix='/favorites')


@favorite_bp.route('/')
@profile_required
def index():
    """Sevimlilar sahifasi - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])
    return render_template('spa.html', user=user)


@favorite_bp.route('/api/list')
@profile_required
def get_favorites():
    """Sevimlilar ro'yxatini olish"""
    current_user = User.query.get(session['user_id'])

    favorites = Favorite.query.filter_by(
        user_id=current_user.id
    ).order_by(Favorite.created_at.desc()).all()

    favorites_data = [fav.to_dict() for fav in favorites]

    return jsonify({
        'favorites': favorites_data,
        'count': len(favorites_data)
    })


@favorite_bp.route('/api/add', methods=['POST'])
@profile_required
def add_favorite():
    """Sevimliga qo'shish"""
    current_user = User.query.get(session['user_id'])
    data = request.get_json()

    favorite_user_id = data.get('user_id')

    if not favorite_user_id:
        return jsonify({'error': 'user_id kerak'}), 400

    # O'zini qo'sha olmasligi
    if favorite_user_id == current_user.id:
        return jsonify({'error': 'O\'zingizni sevimliga qo\'sha olmaysiz'}), 400

    # Foydalanuvchi mavjudligini tekshirish
    favorite_user = User.query.get(favorite_user_id)
    if not favorite_user or not favorite_user.profile or not favorite_user.profile.is_active:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    # Allaqachon sevimliga qo'shilganmi?
    existing_favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        favorite_user_id=favorite_user_id
    ).first()

    if existing_favorite:
        return jsonify({'error': 'Allaqachon sevimliga qo\'shilgan'}), 400

    # Sevimliga qo'shish
    new_favorite = Favorite(
        user_id=current_user.id,
        favorite_user_id=favorite_user_id
    )
    db.session.add(new_favorite)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Sevimliga qo\'shildi',
        'favorite': new_favorite.to_dict()
    })


@favorite_bp.route('/api/<int:favorite_id>/remove', methods=['POST'])
@profile_required
def remove_favorite(favorite_id):
    """Sevimlidan olib tashlash"""
    current_user = User.query.get(session['user_id'])

    favorite = Favorite.query.get(favorite_id)

    if not favorite:
        return jsonify({'error': 'Sevimli topilmadi'}), 404

    # Foydalanuvchi ekanligini tekshirish
    if favorite.user_id != current_user.id:
        return jsonify({'error': 'Bu sevimlini olib tashla olmaysiz'}), 403

    db.session.delete(favorite)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Sevimlidan olib tashlandi'
    })
