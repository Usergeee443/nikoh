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


@feed_bp.route('/api/listings')
@basic_profile_required
def get_listings():
    """E'lonlarni olish (API)"""
    current_user = User.query.get(session['user_id'])
    current_profile = current_user.profile

    # Pagination — birinchi sahifa tez yuklansi uchun kamroq (6 ta)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = max(1, min(per_page, 50))

    # Filterlar
    show_top_only = request.args.get('top_only', 'false') == 'true'

    # Base query
    query = Profile.query.filter(
        Profile.is_active == True,
        Profile.user_id != current_user.id
    )

    # Jinsi bo'yicha filter (qarshi jins)
    # Avval qarshi jins bo'yicha filter qo'llaymiz
    if current_profile.gender == 'Erkak':
        opposite_gender = 'Ayol'
    else:
        opposite_gender = 'Erkak'
    
    # Qarshi jins bo'yicha filter qo'llash
    query_with_gender = query.filter(Profile.gender == opposite_gender)
    
    # Agar qarshi jins bo'yicha e'lonlar topilmasa, jins filterini qoldiramiz
    # (bu test uchun, keyinroq o'chirilishi mumkin)
    # Avval tekshiramiz, qarshi jins bo'yicha e'lonlar bormi?
    # exists() ishlatamiz, bu count() dan tezroq
    has_opposite_gender = db.session.query(query_with_gender.exists()).scalar()
    
    if has_opposite_gender:
        # Qarshi jins bo'yicha e'lonlar bor, filter qo'llaymiz
        query = query_with_gender
    # Agar qarshi jins bo'yicha e'lonlar yo'q bo'lsa, jins filterini qoldiramiz
    # (query o'zgarishsiz qoladi - faqat is_active va user_id filterlari qoladi)

    # Juftga talablar filterlari olib tashlandi
    # Bu filterlar ilovani ochgandan keyin filter funksiyasi orqali ishlatilishi mumkin

    # User bilan join qilish (zarur, chunki UserTariff bilan join qilish uchun)
    query = query.join(User)
    
    # TOP e'lonlar
    from models.tariff import UserTariff
    
    if show_top_only:
        # Faqat TOP tarifga ega foydalanuvchilarni ko'rsatish
        query = query.join(UserTariff, db.and_(
            UserTariff.user_id == User.id,
            UserTariff.is_active == True,
            UserTariff.is_top == True,
            db.or_(
                UserTariff.top_expires_at.is_(None),
                UserTariff.top_expires_at > datetime.utcnow()
            )
        ))
    else:
        # TOP e'lonlarni birinchi o'ringa qo'yish uchun outerjoin
        query = query.outerjoin(
            UserTariff, 
            db.and_(
                UserTariff.user_id == User.id,
                UserTariff.is_active == True,
                UserTariff.is_top == True,
                db.or_(
                    UserTariff.top_expires_at.is_(None),
                    UserTariff.top_expires_at > datetime.utcnow()
                )
            )
        )

    # Saralash: avval TOP, keyin yangilari
    # Faqat is_active == True bo'lgan e'lonlar ko'rsatilishi kerak (allaqachon filter qilingan)
    # UserTariff.is_top NULL bo'lishi mumkin, shuning uchun CASE ishlatamiz
    query = query.order_by(
        db.desc(case((UserTariff.is_top == True, 1), else_=0)),
        db.desc(Profile.activated_at)
    )

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    profiles = pagination.items
    
    # Current user'ning favorites list'ini olish
    user_favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    favorite_user_ids = {fav.favorite_user_id for fav in user_favorites}

    # JSON formatga o'tkazish
    listings = []
    for profile in profiles:
        # TOP statusini tekshirish
        is_top = False
        if profile.user.has_active_tariff:
            active_tariff = profile.user.active_tariff
            if active_tariff and active_tariff.is_top and not active_tariff.is_top_expired:
                is_top = True

        listing = profile.to_dict()
        listing['is_top'] = is_top
        listing['user_id'] = profile.user_id
        listing['is_favorite'] = profile.user_id in favorite_user_ids

        listings.append(listing)

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
