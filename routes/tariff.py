from flask import Blueprint, render_template, request, session, jsonify
from models import User, UserTariff
from database import db
from routes.auth import login_required
from config import Config

tariff_bp = Blueprint('tariff', __name__, url_prefix='/tariff')


@tariff_bp.route('/purchase')
@login_required
def purchase():
    """Tarif sotib olish sahifasi"""
    user = User.query.get(session['user_id'])

    tariff_info = {
        'name': 'KUMUSH',
        'price': Config.KUMUSH_TARIFF_PRICE,
        'requests': Config.KUMUSH_TARIFF_REQUESTS,
        'days': Config.KUMUSH_TARIFF_DAYS,
        'top_days': Config.KUMUSH_TARIFF_TOP_DAYS,
        'card_number': Config.PAYMENT_CARD_NUMBER,
        'card_name': Config.PAYMENT_CARD_NAME
    }

    return render_template('tariff/purchase.html',
                         user=user,
                         tariff=tariff_info)


@tariff_bp.route('/api/status')
@login_required
def get_status():
    """Foydalanuvchining tarif holatini olish"""
    user = User.query.get(session['user_id'])

    if not user.has_active_tariff:
        return jsonify({
            'has_active_tariff': False,
            'tariff': None
        })

    active_tariff = user.active_tariff

    return jsonify({
        'has_active_tariff': True,
        'tariff': {
            'name': active_tariff.tariff_name,
            'requests_count': active_tariff.requests_count,
            'total_requests': active_tariff.total_requests,
            'is_top': active_tariff.is_top and not active_tariff.is_top_expired,
            'days_remaining': active_tariff.days_remaining,
            'expires_at': active_tariff.expires_at.isoformat() if active_tariff.expires_at else None
        }
    })


@tariff_bp.route('/my-tariffs')
@login_required
def my_tariffs():
    """Mening tariflarim"""
    user = User.query.get(session['user_id'])

    # Barcha tariflar (aktiv va o'tgan)
    tariffs = UserTariff.query.filter_by(user_id=user.id).order_by(
        UserTariff.created_at.desc()
    ).all()

    return render_template('tariff/my_tariffs.html',
                         user=user,
                         tariffs=tariffs)


@tariff_bp.route('/payment-instructions')
@login_required
def payment_instructions():
    """To'lov yo'riqnomasi"""
    user = User.query.get(session['user_id'])

    tariff_info = {
        'name': 'KUMUSH',
        'price': Config.KUMUSH_TARIFF_PRICE,
        'card_number': Config.PAYMENT_CARD_NUMBER,
        'card_name': Config.PAYMENT_CARD_NAME
    }

    return render_template('tariff/payment_instructions.html',
                         user=user,
                         tariff=tariff_info)
