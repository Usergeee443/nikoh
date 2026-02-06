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
        'country': getattr(profile, 'country', None),
        'region': profile.region,
        'nationality': profile.nationality,
        'marital_status': profile.marital_status,
        'height': profile.height,
        'weight': profile.weight,
        'religious_level': profile.religious_level,
        'education': profile.education,
        'profession': getattr(profile, 'profession', None),
        'salary': getattr(profile, 'salary', None),
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
    # Filterlar
    request_regions = request.args.get('regions', type=str)
    request_marital = request.args.get('marital_status', type=str)
    request_aqida = request.args.get('aqida', type=str)
    request_prays = request.args.get('prays', type=str)
    request_religious_level = request.args.get('religious_level', type=str)
    request_quran = request.args.get('quran_reading', type=str)
    request_mazhab = request.args.get('mazhab', type=str)
    request_education = request.args.get('education', type=str)
    request_profession = request.args.get('profession', type=str)
    request_age_min = request.args.get('age_min', type=int)
    request_age_max = request.args.get('age_max', type=int)
    request_height_min = request.args.get('height_min', type=int)
    request_height_max = request.args.get('height_max', type=int)
    request_weight_min = request.args.get('weight_min', type=int)
    request_weight_max = request.args.get('weight_max', type=int)
    request_has_salary = request.args.get('has_salary', type=str)  # 'true' = faqat maosh kiritganlar
    request_salary_min = request.args.get('salary_min', type=int)
    request_salary_max = request.args.get('salary_max', type=int)
    request_smoking = request.args.get('smoking', type=str)
    request_sport_days_min = request.args.get('sport_days_min', type=int)

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

    if request_regions and request_regions.strip():
        regions_list = [r.strip() for r in request_regions.split(',') if r.strip()]
        if regions_list:
            query = query.filter(Profile.region.in_(regions_list))
    if request_marital and request_marital.strip():
        query = query.filter(Profile.marital_status == request_marital.strip())
    if request_aqida and request_aqida.strip():
        query = query.filter(Profile.aqida == request_aqida.strip())
    if request_prays and request_prays.strip():
        query = query.filter(Profile.prays == request_prays.strip())
    if request_religious_level and request_religious_level.strip():
        query = query.filter(Profile.religious_level == request_religious_level.strip())
    if request_quran and request_quran.strip():
        query = query.filter(Profile.quran_reading == request_quran.strip())
    if request_mazhab and request_mazhab.strip():
        query = query.filter(Profile.mazhab == request_mazhab.strip())
    if request_education and request_education.strip():
        query = query.filter(Profile.education == request_education.strip())
    if request_profession and request_profession.strip():
        query = query.filter(Profile.profession.ilike('%' + request_profession.strip() + '%'))
    if request_age_min is not None and request_age_min > 0:
        year_max = datetime.utcnow().year - request_age_min
        query = query.filter(Profile.birth_year <= year_max)
    if request_age_max is not None and request_age_max > 0:
        year_min = datetime.utcnow().year - request_age_max
        query = query.filter(Profile.birth_year >= year_min)
    if request_height_min is not None and request_height_min > 0:
        query = query.filter(Profile.height >= request_height_min)
    if request_height_max is not None and request_height_max > 0:
        query = query.filter(Profile.height <= request_height_max)
    if request_weight_min is not None and request_weight_min > 0:
        query = query.filter(Profile.weight >= request_weight_min)
    if request_weight_max is not None and request_weight_max > 0:
        query = query.filter(Profile.weight <= request_weight_max)
    if request_smoking and request_smoking.strip():
        query = query.filter(Profile.smoking == request_smoking.strip())
    if request_sport_days_min is not None and request_sport_days_min > 0:
        query = query.filter(Profile.sport_days >= request_sport_days_min)
    if request_has_salary == 'true':
        query = query.filter(Profile.salary.isnot(None), Profile.salary != '')
    # Salary min/max: DB darajasida aniq solishtirish qiyin (string).
    # Kamida salary bo'sh bo'lmaganlarini cheklaymiz, keyin paginationdan keyin post-filter qilamiz.
    salary_range_requested = (request_salary_min is not None and request_salary_min > 0) or (request_salary_max is not None and request_salary_max > 0)
    if salary_range_requested:
        query = query.filter(Profile.salary.isnot(None), Profile.salary != '')

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

    # Salary min/max post-filter (string -> number)
    # Eslatma: bu taxminiy. Masalan "3-5 mln" kabi formatlarda birinchi raqam olinadi.
    if 'salary_range_requested' in locals() and salary_range_requested and profiles:
        import re

        def _salary_to_int(s):
            if not s:
                return None
            m = re.search(r'(\d+)', str(s).replace(',', ''))
            if not m:
                return None
            try:
                return int(m.group(1))
            except ValueError:
                return None

        filtered = []
        for p in profiles:
            val = _salary_to_int(getattr(p, 'salary', None))
            if val is None:
                continue
            if request_salary_min is not None and request_salary_min > 0 and val < request_salary_min:
                continue
            if request_salary_max is not None and request_salary_max > 0 and val > request_salary_max:
                continue
            filtered.append(p)
        profiles = filtered

    # Tez javob: per_page=1 da qo'shimcha so'rovlarni o'tkazib yuboramiz (birinchi kartochka tez chiqadi)
    quick_first_paint = (page == 1 and per_page == 1)
    top_user_ids = set()
    favorite_user_ids = set()
    if not quick_first_paint and profiles:
        from models.tariff import UserTariff as UT
        rows = db.session.query(UT.user_id).filter(
            UT.is_active == True,
            UT.is_top == True,
            UT.user_id.in_([p.user_id for p in profiles]),
            db.or_(UT.top_expires_at.is_(None), UT.top_expires_at > now)
        ).distinct().all()
        top_user_ids = {r[0] for r in rows}
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
    """Bitta e'lonni batafsil ko'rish (profile_id berilsa shu profil)"""
    current_user = User.query.get(session['user_id'])
    profile_id = request.args.get('profile_id', type=int)

    # O'zini ko'ra olmasligi
    if user_id == current_user.id:
        return jsonify({'error': 'O\'zingizni ko\'ra olmaysiz'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Foydalanuvchi topilmadi'}), 404

    if profile_id:
        profile = Profile.query.filter_by(id=profile_id, user_id=user.id).first()
    else:
        profile = user.profile
    if not profile or not profile.is_active:
        return jsonify({'error': 'Profil topilmadi'}), 404
    profile_data = profile.to_dict()

    # TOP statusini qo'shish
    is_top = False
    if user.has_active_tariff:
        active_tariff = user.active_tariff
        if active_tariff and active_tariff.is_top and not active_tariff.is_top_expired:
            is_top = True

    profile_data['is_top'] = is_top
    profile_data['user_id'] = user.id

    # Allaqachon so'rov yuborilganmi? (xuddi shu profil uchun)
    from models import MatchRequest
    q_sent = db.and_(MatchRequest.sender_id == current_user.id, MatchRequest.receiver_id == user.id)
    q_received = db.and_(MatchRequest.sender_id == user.id, MatchRequest.receiver_id == current_user.id)
    if profile.id:
        q_sent = db.and_(q_sent, MatchRequest.receiver_profile_id == profile.id)
        q_received = db.and_(q_received, MatchRequest.receiver_profile_id == profile.id)
    else:
        q_sent = db.and_(q_sent, MatchRequest.receiver_profile_id.is_(None))
        q_received = db.and_(q_received, MatchRequest.receiver_profile_id.is_(None))
    existing_request = MatchRequest.query.filter(db.or_(q_sent, q_received)).first()

    profile_data['request_sent'] = existing_request is not None
    if existing_request:
        profile_data['request_status'] = existing_request.status
        profile_data['is_sender'] = existing_request.sender_id == current_user.id
        # Agar so'rov qabul qilingan bo'lsa, chat_id ni qo'shamiz
        if existing_request.status == 'accepted' and existing_request.chat:
            profile_data['chat_id'] = existing_request.chat.id

    # Shu foydalanuvchining boshqa aktiv e'lonlari
    other_profiles = Profile.query.filter(
        Profile.user_id == user.id,
        Profile.is_active == True,
        Profile.id != profile.id
    ).all()
    if other_profiles:
        profile_data['other_listings'] = [_listing_dict(p, is_top=False, is_favorite=False) for p in other_profiles]

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
