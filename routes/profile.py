from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import User, Profile
from database import db
from routes.auth import login_required
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
            profile.region = request.form.get('region') or profile.region
            profile.nationality = request.form.get('nationality') or profile.nationality
            profile.marital_status = request.form.get('marital_status') or profile.marital_status
            
            height = request.form.get('height')
            if height:
                profile.height = int(height)
            weight = request.form.get('weight')
            if weight:
                profile.weight = int(weight)
            
            profile.aqida = request.form.get('aqida') or profile.aqida
            profile.prays = request.form.get('prays') or profile.prays
            profile.fasts = request.form.get('fasts') or profile.fasts
            profile.quran_reading = request.form.get('quran_reading') or profile.quran_reading
            profile.mazhab = request.form.get('mazhab') or profile.mazhab
            profile.religious_level = request.form.get('religious_level') or profile.religious_level
            profile.education = request.form.get('education') or profile.education
            profile.profession = request.form.get('profession') or profile.profession
            
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
            
            profile.partner_region = request.form.get('partner_region') or profile.partner_region
            profile.partner_religious_level = request.form.get('partner_religious_level') or profile.partner_religious_level
            profile.partner_marital_status = request.form.get('partner_marital_status') or profile.partner_marital_status

            # is_complete property avtomatik barcha maydonlar to'ldirilganini tekshiradi
            # Shuning uchun uni alohida set qilish shart emas

            db.session.commit()

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
