from flask import Blueprint, render_template, request, session, jsonify
from models import User, Profile
from database import db
from routes.auth import login_required, profile_required
from sqlalchemy import and_, or_
from datetime import datetime

feed_bp = Blueprint('feed', __name__, url_prefix='/feed')


@feed_bp.route('/')
@profile_required
def index():
    """E'lonlar sahifasi (Feed) - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])
    # SPA sahifasiga yo'naltirish
    return render_template('spa.html', user=user)


@feed_bp.route('/api/listings')
@profile_required
def get_listings():
    """E'lonlarni olish (API)"""
    current_user = User.query.get(session['user_id'])
    current_profile = current_user.profile

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Filterlar
    show_top_only = request.args.get('top_only', 'false') == 'true'

    # Base query
    query = Profile.query.filter(
        Profile.is_active == True,
        Profile.user_id != current_user.id
    )

    # Jinsi bo'yicha filter (qarshi jins)
    if current_profile.gender == 'Erkak':
        query = query.filter(Profile.gender == 'Ayol')
    else:
        query = query.filter(Profile.gender == 'Erkak')

    # Foydalanuvchining talablariga mos
    if current_profile.partner_age_min and current_profile.partner_age_max:
        current_year = datetime.utcnow().year
        birth_year_max = current_year - current_profile.partner_age_min
        birth_year_min = current_year - current_profile.partner_age_max
        query = query.filter(
            and_(
                Profile.birth_year >= birth_year_min,
                Profile.birth_year <= birth_year_max
            )
        )

    # Hudud bo'yicha
    if current_profile.partner_region and current_profile.partner_region != 'Farqi yo\'q':
        query = query.filter(Profile.region == current_profile.partner_region)

    # Diniy daraja
    if current_profile.partner_religious_level and current_profile.partner_religious_level != 'Farqi yo\'q':
        query = query.filter(Profile.religious_level == current_profile.partner_religious_level)

    # Oilaviy holat
    if current_profile.partner_marital_status and current_profile.partner_marital_status != 'Farqi yo\'q':
        query = query.filter(Profile.marital_status == current_profile.partner_marital_status)

    # TOP e'lonlar
    if show_top_only:
        # Faqat TOP tarifga ega foydalanuvchilarni ko'rsatish
        query = query.join(User).join(User.tariffs).filter(
            db.and_(
                User.tariffs.any(is_active=True),
                User.tariffs.any(is_top=True)
            )
        )

    # Saralash: avval TOP, keyin yangilari
    query = query.outerjoin(User).outerjoin(User.tariffs).order_by(
        db.desc(User.tariffs.any(is_top=True)),
        db.desc(Profile.activated_at)
    )

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    profiles = pagination.items

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
@profile_required
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
    existing_request = MatchRequest.query.filter_by(
        sender_id=current_user.id,
        receiver_id=user.id
    ).first()

    profile_data['request_sent'] = existing_request is not None
    if existing_request:
        profile_data['request_status'] = existing_request.status

    return jsonify(profile_data)
