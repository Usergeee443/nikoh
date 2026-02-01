from flask import Blueprint, render_template, request, session, jsonify
from models import User, Profile, Favorite
from database import db
from routes.auth import login_required, profile_required, basic_profile_required
from sqlalchemy import and_, or_, case
from datetime import datetime

feed_bp = Blueprint('feed', __name__, url_prefix='/feed')


@feed_bp.route('/')
@basic_profile_required
def index():
    """E'lonlar sahifasi (Feed) - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])
    # SPA sahifasiga yo'naltirish
    return render_template('spa.html', user=user)


def _listing_dict(profile, is_top, is_favorite):
    """Ro'yxat kartochkasi uchun yengil JSON (N+1 va to'liq to_dict dan qochish)."""
    age = (datetime.utcnow().year - profile.birth_year) if profile.birth_year else None
    return {
        'id': profile.id,
        'user_id': profile.user_id,
        'name': profile.name,
        'age': age,
        'gender': profile.gender,
        'region': profile.region,
        'nationality': profile.nationality,
        'marital_status': profile.marital_status,
        'height': profile.height,
        'weight': profile.weight,
        'religious_level': profile.religious_level,
        'education': profile.education,
        'views': 0,
        'likes': 0,
        'is_top': is_top,
        'is_favorite': is_favorite,
    }


@feed_bp.route('/api/listings')
@basic_profile_required
def get_listings():
    """E'lonlarni olish (API) — N+1 bartaraf, yengil JSON."""
    current_user = User.query.get(session['user_id'])
    current_profile = current_user.profile

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = max(1, min(per_page, 50))

    show_top_only = request.args.get('top_only', 'false') == 'true'
    request_gender = request.args.get('gender', type=str)
    request_sort = request.args.get('sort', 'new', type=str)

    # Jins: to'g'ridan-to'g'ri filter (exists() so'rov olib tashlandi)
    if request_gender in ('Erkak', 'Ayol'):
        filter_gender = request_gender
    else:
        filter_gender = 'Ayol' if current_profile.gender == 'Erkak' else 'Erkak'

    query = Profile.query.filter(
        Profile.is_active == True,
        Profile.user_id != current_user.id,
        Profile.gender == filter_gender
    ).join(User)

    from models.tariff import UserTariff
    now = datetime.utcnow()
    top_condition = db.and_(
        UserTariff.user_id == User.id,
        UserTariff.is_active == True,
        UserTariff.is_top == True,
        db.or_(UserTariff.top_expires_at.is_(None), UserTariff.top_expires_at > now)
    )

    if show_top_only:
        query = query.join(UserTariff, top_condition)
    else:
        query = query.outerjoin(UserTariff, top_condition)

    # Saralash: new, name_asc, name_desc, age_asc, age_desc, height_asc, height_desc
    top_first = db.desc(case((UserTariff.is_top == True, 1), else_=0))
    if request_sort == 'name_asc':
        query = query.order_by(top_first, Profile.name.asc())
    elif request_sort == 'name_desc':
        query = query.order_by(top_first, Profile.name.desc())
    elif request_sort == 'age_asc':
        query = query.order_by(top_first, Profile.birth_year.asc())   # yosh katta birinchi
    elif request_sort == 'age_desc':
        query = query.order_by(top_first, Profile.birth_year.desc())  # yosh kichik birinchi
    elif request_sort == 'height_asc':
        query = query.order_by(top_first, Profile.height.asc(), db.desc(Profile.activated_at))
    elif request_sort == 'height_desc':
        query = query.order_by(top_first, Profile.height.desc(), db.desc(Profile.activated_at))
    else:
        query = query.order_by(top_first, db.desc(Profile.activated_at))  # new

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    profiles = pagination.items

    # Bitta so'rov: TOP bo'lgan user_id lar (N+1 yo'q)
    top_user_ids = set()
    if profiles:
        from models.tariff import UserTariff as UT
        rows = db.session.query(UT.user_id).filter(
            UT.is_active == True,
            UT.is_top == True,
            UT.user_id.in_([p.user_id for p in profiles]),
            db.or_(UT.top_expires_at.is_(None), UT.top_expires_at > now)
        ).distinct().all()
        top_user_ids = {r[0] for r in rows}

    # Bitta so'rov: joriy foydalanuvchi sevimlilari
    favorite_user_ids = {fav.favorite_user_id for fav in Favorite.query.filter_by(user_id=current_user.id).all()}

    listings = [
        _listing_dict(
            profile,
            is_top=(profile.user_id in top_user_ids),
            is_favorite=(profile.user_id in favorite_user_ids)
        )
        for profile in profiles
    ]

    return jsonify({
        'listings': listings,
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    })


@feed_bp.route('/api/listing/<int:user_id>')
@basic_profile_required
def get_listing_detail(user_id):
    """Bitta e'lonni batafsil ko'rish"""
    current_user = User.query.get(session['user_id'])

    # O'zini ko'ra olmasligi
    if user_id == current_user.id:
        return jsonify({'error': 'O\'zingizni ko\'ra olmaysiz'}), 400

    user = User.query.get(user_id)

    if not user or not user.profile or not user.profile.is_active:
        return jsonify({'error': 'Profil topilmadi'}), 404

    profile = user.profile
    profile_data = profile.to_dict()

    # TOP statusini qo'shish
    is_top = False
    if user.has_active_tariff:
        active_tariff = user.active_tariff
        if active_tariff and active_tariff.is_top and not active_tariff.is_top_expired:
            is_top = True

    profile_data['is_top'] = is_top
    profile_data['user_id'] = user.id

    # Allaqachon so'rov yuborilganmi?
    from models import MatchRequest
    # Ikki tomonlama so'rovni tekshirish
    existing_request = MatchRequest.query.filter(
        db.or_(
            db.and_(MatchRequest.sender_id == current_user.id, MatchRequest.receiver_id == user.id),
            db.and_(MatchRequest.sender_id == user.id, MatchRequest.receiver_id == current_user.id)
        )
    ).first()

    profile_data['request_sent'] = existing_request is not None
    if existing_request:
        profile_data['request_status'] = existing_request.status
        profile_data['is_sender'] = existing_request.sender_id == current_user.id
        # Agar so'rov qabul qilingan bo'lsa, chat_id ni qo'shamiz
        if existing_request.status == 'accepted' and existing_request.chat:
            profile_data['chat_id'] = existing_request.chat.id

    return jsonify(profile_data)


@feed_bp.route('/profile/<int:user_id>')
@basic_profile_required
def profile_detail(user_id):
    """Profil batafsil ko'rish sahifasi"""
    current_user = User.query.get(session['user_id'])
    
    # O'zini ko'ra olmasligi
    if user_id == current_user.id:
        return render_template('error.html', message="O'zingizni ko'ra olmaysiz"), 400
    
    user = User.query.get(user_id)
    
    if not user or not user.profile or not user.profile.is_active:
        return render_template('error.html', message="Profil topilmadi"), 404
    
    # Allaqachon so'rov yuborilganmi?
    from models import MatchRequest
    existing_request = MatchRequest.query.filter_by(
        sender_id=current_user.id,
        receiver_id=user.id
    ).first()
    
    request_sent = existing_request is not None
    
    return render_template('feed/profile_detail.html', 
                         profile=user.profile, 
                         current_user=current_user,
                         request_sent=request_sent)
