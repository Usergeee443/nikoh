from flask import Blueprint

# Blueprintlarni import qilish
from .auth import auth_bp
from .profile import profile_bp
from .feed import feed_bp
from .tariff import tariff_bp
from .request import request_bp
from .chat import chat_bp
from .admin import admin_bp


def register_blueprints(app):
    """Barcha blueprintlarni ro'yxatdan o'tkazish"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(tariff_bp)
    app.register_blueprint(request_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)
