from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import User, Profile
from database import db
from routes.auth import login_required, invalidate_user_data_cache
from datetime import datetime

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('/onboarding')
@login_required
def onboarding():
    """Onboarding endi SPA ichida bajariladi - eski yo'lni SPA ga yo'naltiramiz"""
    user = User.query.get(session['user_id'])
    return render_template('spa.html', user=user)


@profile_bp.route('/onboarding/step1', methods=['GET', 'POST'])
@login_required
def onboarding_step1():
    """Qadam 1: Shaxsiy ma'lumotlar"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        profile = user.profile
        profile.name = request.form.get('name')
        profile.gender = request.form.get('gender')
        profile.birth_year = int(request.form.get('birth_year'))
        profile.region = request.form.get('region')
        profile.nationality = request.form.get('nationality')
        profile.marital_status = request.form.get('marital_status')

        db.session.commit()
        return redirect(url_for('profile.view'))

    # Endi onboarding alohida sahifa emas, SPA ichida bajariladi
    return render_template('spa.html', user=user)


@profile_bp.route('/onboarding/step2', methods=['GET', 'POST'])
@login_required
def onboarding_step2():
    """Qadam 2: Jismoniy ma'lumotlar"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        profile = user.profile
        profile.height = int(request.form.get('height'))
        profile.weight = int(request.form.get('weight'))

        db.session.commit()
        return redirect(url_for('profile.view'))

    return render_template('spa.html', user=user)


@profile_bp.route('/onboarding/step3', methods=['GET', 'POST'])
@login_required
def onboarding_step3():
    """Qadam 3: Diniy ma'lumotlar"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        profile = user.profile
        profile.prays = request.form.get('prays')
        profile.fasts = request.form.get('fasts')
        profile.religious_level = request.form.get('religious_level')

        db.session.commit()
        return redirect(url_for('profile.view'))

    return render_template('spa.html', user=user)


@profile_bp.route('/onboarding/step4', methods=['GET', 'POST'])
@login_required
def onboarding_step4():
    """Qadam 4: Ta'lim va kasb"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        profile = user.profile
        profile.education = request.form.get('education')
        profile.profession = request.form.get('profession')
        profile.is_working = request.form.get('is_working') == 'true'

        db.session.commit()
        return redirect(url_for('profile.view'))

    return render_template('spa.html', user=user)


@profile_bp.route('/onboarding/step5', methods=['GET', 'POST'])
@login_required
def onboarding_step5():
    """Qadam 5: Juftga qo'yiladigan talablar"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        profile = user.profile
        profile.partner_age_min = int(request.form.get('partner_age_min'))
        profile.partner_age_max = int(request.form.get('partner_age_max'))
        ploc = request.form.get('partner_locations')
        if ploc is not None and ploc.strip():
            profile.partner_locations = ploc.strip()[:4000] or None
        else:
            profile.partner_country = request.form.get('partner_country') or profile.partner_country
            profile.partner_region = request.form.get('partner_region')
        profile.partner_religious_level = request.form.get('partner_religious_level')
        profile.partner_marital_status = request.form.get('partner_marital_status')

        db.session.commit()
        return redirect(url_for('profile.view'))

    return render_template('spa.html', user=user)


@profile_bp.route('/onboarding/complete', methods=['GET', 'POST'])
@login_required
def onboarding_complete():
    """Onboarding tugallandi"""
    user = User.query.get(session['user_id'])

    # Agar profil to'liq emas bo'lsa, profil sahifasiga qaytarish
    if not user.profile or not user.profile.is_complete:
        return redirect(url_for('profile.view'))

    # Agar bio allaqachon to'ldirilgan bo'lsa, activate sahifasiga yo'naltirish
    if user.profile.bio:
        return redirect(url_for('profile.activate_profile'))

    if request.method == 'POST':
        bio = request.form.get('bio')
        user.profile.bio = bio
        db.session.commit()

        return redirect(url_for('profile.activate_profile'))

    return render_template('spa.html', user=user)


@profile_bp.route('/activate', methods=['GET', 'POST'])
@login_required
def activate_profile():
    """E'lonni faollashtirish - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])

    if not user.profile_completed:
        return redirect(url_for('profile.onboarding'))

    if request.method == 'POST':
        # E'lonni faollashtirish uchun tarif kerak
        if not user.has_active_tariff:
            return redirect(url_for('tariff.purchase'))

        user.profile.activate()
        return redirect(url_for('feed.index'))

    # SPA ga yo'naltirish (tarif bo'lmasa ham ko'rish mumkin)
    return render_template('spa.html', user=user)


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    """Profilni tahrirlash"""
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        try:
            profile = user.profile

            # Yangilanadigan maydonlar - to'g'ri tekshirib olish
            phone_number = request.form.get('phone_number')
            if phone_number is not None:
                profile.phone_number = phone_number.strip() or profile.phone_number
            profile.name = request.form.get('name') or profile.name
            profile.gender = request.form.get('gender') or profile.gender
            birth_year = request.form.get('birth_year')
            if birth_year:
                profile.birth_year = int(birth_year)
            profile.country = request.form.get('country') or profile.country
            profile.region = request.form.get('region') or profile.region
            profile.nationality = request.form.get('nationality') or profile.nationality
            profile.marital_status = request.form.get('marital_status') or profile.marital_status
            
            height = request.form.get('height')
            if height:
                profile.height = int(height)
            weight = request.form.get('weight')
            if weight:
                profile.weight = int(weight)
            profile.smoking = (request.form.get('smoking') or '').strip()[:20] or profile.smoking
            sd = request.form.get('sport_days')
            if sd is not None and sd != '':
                try:
                    profile.sport_days = int(sd) if 0 <= int(sd) <= 7 else profile.sport_days
                except ValueError:
                    pass
            
            profile.aqida = request.form.get('aqida') or profile.aqida
            profile.prays = request.form.get('prays') or profile.prays
            profile.fasts = request.form.get('fasts') or profile.fasts
            profile.quran_reading = request.form.get('quran_reading') or profile.quran_reading
            profile.mazhab = request.form.get('mazhab') or profile.mazhab
            profile.religious_level = request.form.get('religious_level') or profile.religious_level
            profile.education = request.form.get('education') or profile.education
            profile.profession = request.form.get('profession') or profile.profession
            profile.salary = (request.form.get('salary') or '').strip() or profile.salary
            
            is_working = request.form.get('is_working')
            if is_working:
                profile.is_working = is_working == 'true'
            
            profile.bio = request.form.get('bio') or profile.bio

            # Juftga qo'yiladigan talablar
            partner_age_min = request.form.get('partner_age_min')
            if partner_age_min:
                profile.partner_age_min = int(partner_age_min)
            partner_age_max = request.form.get('partner_age_max')
            if partner_age_max:
                profile.partner_age_max = int(partner_age_max)
            
            ploc = request.form.get('partner_locations')
            if ploc is not None and ploc.strip():
                profile.partner_locations = ploc.strip()[:4000] or None
            else:
                profile.partner_country = request.form.get('partner_country') or profile.partner_country
                profile.partner_region = request.form.get('partner_region') or profile.partner_region
            profile.partner_religious_level = request.form.get('partner_religious_level') or profile.partner_religious_level
            profile.partner_marital_status = request.form.get('partner_marital_status') or profile.partner_marital_status

            # is_complete property avtomatik barcha maydonlar to'ldirilganini tekshiradi
            # Shuning uchun uni alohida set qilish shart emas

            db.session.commit()
            invalidate_user_data_cache(session.get('user_id'))

            # SPA da yana profilga qaytarish uchun JSON javob
            return jsonify({'success': True, 'message': 'Profil saqlandi'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Xatolik: {str(e)}'}), 400

    # GET so'rovi uchun SPA ga yo'naltirish
    return render_template('spa.html', user=user)


@profile_bp.route('/view')
@login_required
def view():
    """O'z profilini ko'rish - SPA ga yo'naltirish"""
    user = User.query.get(session['user_id'])
    return render_template('spa.html', user=user)


@profile_bp.route('/toggle-active', methods=['POST'])
@login_required
def toggle_active():
    """E'lonni yoqish/o'chirish"""
    user = User.query.get(session['user_id'])

    if user.profile.is_active:
        user.profile.deactivate()
        message = "E'lon o'chirildi"
    else:
        if not user.profile_completed:
            return jsonify({'error': "To'liq profil to'ldiring"}), 400
        if not user.has_active_tariff:
            return jsonify({'error': 'Tarif kerak'}), 400

        user.profile.activate()
        message = "E'lon faollashtirildi"

    return jsonify({
        'success': True,
        'message': message,
        'is_active': user.profile.is_active
    })


@profile_bp.route('/api/progress')
@login_required
def get_progress():
    """Profil to'ldirilganlik foizini olish"""
    user = User.query.get(session['user_id'])

    return jsonify({
        'completion_percentage': user.profile.completion_percentage,
        'is_complete': user.profile.is_complete
    })


@profile_bp.route('/api/listings', methods=['GET'])
@login_required
def list_my_listings():
    """Mening barcha e'lonlarim (asosiy + qo'shimcha — aka/opa uchun)"""
    user = User.query.get(session['user_id'])
    profiles = user.profiles.order_by(Profile.is_primary.desc(), Profile.id).all()
    return jsonify({
        'listings': [p.to_dict() for p in profiles],
        'profiles': [{'id': p.id, 'name': p.name or 'E\'lon', 'is_primary': p.is_primary, 'is_active': p.is_active, 'is_published': getattr(p, 'is_published', True)} for p in profiles]
    })


def _parse_bool(v):
    """JSON true/false yoki 'true'/'false' string ni boolean ga aylantirish"""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ('true', '1', 'ha', 'yes')
    return bool(v)


def _parse_int(v):
    try:
        return int(v) if v not in (None, '') else None
    except (TypeError, ValueError):
        return None


def _normalize_partner_locations(v):
    """partner_locations ni JSON string yoki list dan to'g'ri TEXT uchun string qilib qaytaradi."""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        try:
            import json
            arr = json.loads(v)
        except Exception:
            return None
    elif isinstance(v, list):
        arr = v
    else:
        return None
    if not arr:
        return None
    out = []
    for item in arr:
        if not isinstance(item, dict):
            continue
        if item.get('all_countries'):
            out.append({'all_countries': True})
            break
        c = item.get('c') or item.get('country')
        if not c or not isinstance(c, str):
            continue
        c = (c or '')[:100]
        if item.get('all'):
            out.append({'c': c, 'all': True})
        else:
            r = item.get('r') or item.get('regions') or item.get('region')
            if isinstance(r, list):
                regions = [str(x)[:100] for x in r if x][:50]
            elif r:
                regions = [str(r)[:100]]
            else:
                continue
            if regions:
                out.append({'c': c, 'r': regions})
    if not out:
        return None
    import json
    return json.dumps(out, ensure_ascii=False)[:4000]


@profile_bp.route('/api/listings', methods=['POST'])
@login_required
def create_listing():
    """Yangi e'lon yaratish (boshqa shaxs uchun — aka, opa, ota va h.k.)"""
    user = User.query.get(session['user_id'])
    data = request.get_json(silent=True) or {}
    # FormData dan kelgan bo'lsa (Content-Type boshqacha)
    if not data and request.content_type and 'application/json' not in request.content_type:
        data = {k: v for k, v in request.form.items()} or {}
    name = (data.get('name') or '').strip()
    gender_raw = data.get('gender')
    gender = None
    if gender_raw is not None and str(gender_raw).strip():
        g = str(gender_raw).strip()
        if g in ('Erkak', 'Ayol'):
            gender = g
        elif g.lower() in ('erkak', 'ayol'):
            gender = g.capitalize()
    if not name or not gender:
        return jsonify({'error': 'Ism va jins kerak', 'message': 'Shaxsiy bo\'limda ism va jinsni to\'ldiring.'}), 400
    birth_year = _parse_int(data.get('birth_year'))

    # Yangi profil — is_primary=False, barcha maydonlar asosiy e'lon kabi
    try:
        profile = Profile(
            user_id=user.id,
            is_primary=False,
            name=name,
            gender=str(gender),
            birth_year=birth_year,
            country=(data.get('country') or '')[:100] or None,
            region=(data.get('region') or '')[:100] or None,
            nationality=(data.get('nationality') or '')[:50] or None,
            marital_status=(data.get('marital_status') or '')[:20] or None,
            height=_parse_int(data.get('height')),
            weight=_parse_int(data.get('weight')),
            smoking=(data.get('smoking') or '')[:20] or None,
            sport_days=(lambda s: s if s is not None and 0 <= s <= 7 else None)(_parse_int(data.get('sport_days'))),
            aqida=(data.get('aqida') or '')[:50] or None,
            prays=(data.get('prays') or '')[:20] or None,
            fasts=(data.get('fasts') or '')[:10] or None,
            quran_reading=(data.get('quran_reading') or '')[:50] or None,
            mazhab=(data.get('mazhab') or '')[:30] or None,
            religious_level=(data.get('religious_level') or '')[:20] or None,
            education=(data.get('education') or '')[:100] or None,
            profession=(data.get('profession') or '')[:100] or None,
            is_working=_parse_bool(data.get('is_working')),
            salary=(data.get('salary') or '').strip()[:100] or None,
            partner_age_min=_parse_int(data.get('partner_age_min')),
            partner_age_max=_parse_int(data.get('partner_age_max')),
            partner_country=(data.get('partner_country') or '')[:100] or None,
            partner_region=(data.get('partner_region') or '')[:100] or None,
            partner_locations=_normalize_partner_locations(data.get('partner_locations')),
            partner_religious_level=(data.get('partner_religious_level') or '')[:20] or None,
            partner_marital_status=(data.get('partner_marital_status') or '')[:20] or None,
            bio=(data.get('bio') or '').strip() or None
        )
        # is_published ni faqat ustun mavjud bo'lsa o'rnatish
        try:
            is_pub = _parse_bool(data.get('is_published')) if data.get('is_published') is not None else False
            profile.is_published = is_pub
            # is_published = True bo'lganda is_active ham True qilish (feed da ko'rsatish uchun)
            if is_pub:
                profile.is_active = True
                profile.activated_at = datetime.utcnow()
        except:
            pass
        db.session.add(profile)
        db.session.commit()
        invalidate_user_data_cache(user.id)
        return jsonify({'success': True, 'profile': profile.to_dict(), 'id': profile.id, 'listing_id': profile.id})
    except Exception as e:
        db.session.rollback()
        err_msg = str(e)
        import traceback
        traceback.print_exc()
        if 'Duplicate' in err_msg or 'UNIQUE' in err_msg or 'unique' in err_msg:
            return jsonify({'error': 'Bunday e\'lon allaqachon mavjud', 'message': 'E\'lon saqlanmadi.'}), 500
        if 'is_published' in err_msg:
            return jsonify({'error': 'Baza migratsiyasi kerak', 'message': 'Serverni qayta ishga tushiring.'}), 500
        return jsonify({'error': err_msg, 'message': 'E\'lon saqlanmadi. Qaytadan urinib ko\'ring.'}), 500


@profile_bp.route('/api/listings/<int:listing_id>', methods=['GET'])
@login_required
def get_listing(listing_id):
    """Bitta e'lonni olish (tahrirlash uchun)"""
    user = User.query.get(session['user_id'])
    profile = Profile.query.filter_by(id=listing_id, user_id=user.id).first()
    if not profile:
        return jsonify({'error': 'E\'lon topilmadi'}), 404
    return jsonify({'success': True, 'listing': profile.to_dict()})


@profile_bp.route('/api/listings/<int:listing_id>', methods=['PUT'])
@login_required
def update_listing(listing_id):
    """E'lonni tahrirlash"""
    user = User.query.get(session['user_id'])
    profile = Profile.query.filter_by(id=listing_id, user_id=user.id).first()
    if not profile:
        return jsonify({'error': 'E\'lon topilmadi'}), 404
    if profile.is_primary:
        return jsonify({'error': 'Asosiy profilni bu yerda tahrirlab bo\'lmaydi'}), 400
    
    data = request.get_json(silent=True) or {}
    
    profile.name = (data.get('name') or profile.name or '').strip()[:100] or profile.name
    if data.get('gender') in ('Erkak', 'Ayol'):
        profile.gender = data.get('gender')
    profile.birth_year = _parse_int(data.get('birth_year')) or profile.birth_year
    profile.country = (data.get('country') or '')[:100] or profile.country
    profile.region = (data.get('region') or '')[:100] or profile.region
    profile.nationality = (data.get('nationality') or '')[:50] or profile.nationality
    profile.marital_status = (data.get('marital_status') or '')[:20] or profile.marital_status
    profile.height = _parse_int(data.get('height')) or profile.height
    profile.weight = _parse_int(data.get('weight')) or profile.weight
    if data.get('smoking') is not None:
        profile.smoking = (data.get('smoking') or '')[:20] or None
    if data.get('sport_days') is not None:
        v = _parse_int(data.get('sport_days'))
        profile.sport_days = v if v is not None and 0 <= v <= 7 else profile.sport_days
    profile.aqida = (data.get('aqida') or '')[:50] or profile.aqida
    profile.prays = (data.get('prays') or '')[:20] or profile.prays
    profile.fasts = (data.get('fasts') or '')[:10] or profile.fasts
    profile.quran_reading = (data.get('quran_reading') or '')[:50] or profile.quran_reading
    profile.mazhab = (data.get('mazhab') or '')[:30] or profile.mazhab
    profile.religious_level = (data.get('religious_level') or '')[:20] or profile.religious_level
    profile.education = (data.get('education') or '')[:100] or profile.education
    profile.profession = (data.get('profession') or '')[:100] or profile.profession
    if data.get('is_working') is not None:
        profile.is_working = _parse_bool(data.get('is_working'))
    profile.salary = (data.get('salary') or '').strip()[:100] or profile.salary
    profile.partner_age_min = _parse_int(data.get('partner_age_min')) or profile.partner_age_min
    profile.partner_age_max = _parse_int(data.get('partner_age_max')) or profile.partner_age_max
    profile.partner_country = (data.get('partner_country') or '')[:100] or profile.partner_country
    profile.partner_region = (data.get('partner_region') or '')[:100] or profile.partner_region
    if data.get('partner_locations') is not None:
        profile.partner_locations = _normalize_partner_locations(data.get('partner_locations'))
    profile.partner_religious_level = (data.get('partner_religious_level') or '')[:20] or profile.partner_religious_level
    profile.partner_marital_status = (data.get('partner_marital_status') or '')[:20] or profile.partner_marital_status
    profile.bio = (data.get('bio') or '').strip() or profile.bio
    if data.get('is_published') is not None:
        profile.is_published = _parse_bool(data.get('is_published'))
        # is_published = True bo'lganda is_active ham True qilish (feed da ko'rsatish uchun)
        if profile.is_published:
            profile.is_active = True
            if not profile.activated_at:
                profile.activated_at = datetime.utcnow()
        else:
            profile.is_active = False
    
    try:
        db.session.commit()
        invalidate_user_data_cache(user.id)
        return jsonify({'success': True, 'listing': profile.to_dict(), 'listing_id': profile.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'message': 'Xatolik yuz berdi'}), 500


@profile_bp.route('/api/listings/<int:listing_id>', methods=['DELETE'])
@login_required
def delete_listing(listing_id):
    """E'lonni o'chirish"""
    user = User.query.get(session['user_id'])
    profile = Profile.query.filter_by(id=listing_id, user_id=user.id).first()
    if not profile:
        return jsonify({'error': 'E\'lon topilmadi'}), 404
    if profile.is_primary:
        return jsonify({'error': 'Asosiy profilni o\'chirib bo\'lmaydi'}), 400
    
    try:
        db.session.delete(profile)
        db.session.commit()
        invalidate_user_data_cache(user.id)
        return jsonify({'success': True, 'message': 'E\'lon o\'chirildi'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@profile_bp.route('/api/listings/<int:listing_id>/publish', methods=['POST'])
@login_required
def toggle_listing_publish(listing_id):
    """E'lonni yoqish/o'chirish (publish/unpublish)"""
    user = User.query.get(session['user_id'])
    profile = Profile.query.filter_by(id=listing_id, user_id=user.id).first()
    if not profile:
        return jsonify({'error': 'E\'lon topilmadi'}), 404
    
    data = request.get_json(silent=True) or {}
    publish = _parse_bool(data.get('publish'))
    
    profile.is_published = publish if publish is not None else not profile.is_published
    # is_published = True bo'lganda is_active ham True qilish (feed da ko'rsatish uchun)
    if profile.is_published:
        profile.is_active = True
        if not profile.activated_at:
            profile.activated_at = datetime.utcnow()
    else:
        profile.is_active = False
    
    try:
        db.session.commit()
        invalidate_user_data_cache(user.id)
        return jsonify({'success': True, 'is_published': profile.is_published, 'is_active': profile.is_active, 'message': 'E\'lon yoqildi' if profile.is_published else 'E\'lon o\'chirildi'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
