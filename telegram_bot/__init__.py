from .bot import setup_bot, send_notification, set_flask_app, send_payment_receipt_to_admin, send_pending_listing_to_admins
import asyncio


def send_notification_sync(telegram_id: int, message: str):
    """Flask/thread dan chaqirish uchun: foydalanuvchiga xabar yuborish (sinxron wrapper)"""
    if not telegram_id:
        return False
    try:
        asyncio.run(send_notification(telegram_id, message))
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("send_notification_sync to %s: %s", telegram_id, e)
        return False


__all__ = ['setup_bot', 'send_notification', 'send_notification_sync', 'set_flask_app', 'send_payment_receipt_to_admin', 'send_pending_listing_to_admins']
