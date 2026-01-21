from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import Config
from database import db
from models import User, PaymentRequest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_bot(app):
    """Telegram botni sozlash"""
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot will not start.")
        return None

    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_receipt))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_'))

    return application


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi - botga kiritish"""
    telegram_user = update.effective_user
    telegram_id = telegram_user.id

    # Foydalanuvchini bazaga saqlash yoki yangilash
    with app.app_context():
        user = User.query.filter_by(telegram_id=telegram_id).first()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=telegram_user.username
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user created: {telegram_id}")

    # Mini App tugmasi
    keyboard = [
        [KeyboardButton(
            text="📱 Mini App'ga kirish",
            web_app=WebAppInfo(url=f"{Config.MINI_APP_URL}?user_id={telegram_id}")
        )]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_message = f"""
🤝 Assalomu alaykum, {telegram_user.first_name}!

NIKOH — halol tanishuv platformasiga xush kelibsiz.

Bu yerda siz:
✅ Xavfsiz va halol muhitda
✅ Aniq maqsad bilan
✅ Maxfiylik asosida

tanishishingiz mumkin.

📱 Davom etish uchun "Mini App'ga kirish" tugmasini bosing.
"""

    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup
    )


async def handle_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov chekini qabul qilish"""
    telegram_user = update.effective_user
    telegram_id = telegram_user.id
    photo = update.message.photo[-1]  # Eng katta rasmni olish
    caption = update.message.caption or ""

    with app.app_context():
        user = User.query.filter_by(telegram_id=telegram_id).first()

        if not user:
            await update.message.reply_text("❌ Avval /start bosing.")
            return

        # To'lov so'rovini yaratish
        payment_request = PaymentRequest(
            user_id=user.id,
            tariff_name='KUMUSH',
            amount=Config.KUMUSH_TARIFF_PRICE,
            receipt_file_id=photo.file_id,
            receipt_message=caption
        )
        db.session.add(payment_request)
        db.session.commit()

        await update.message.reply_text(
            "✅ To'lov cheki qabul qilindi!\n\n"
            "Admin tekshirgach sizga xabar beriladi.\n"
            "Bu 1-2 soat vaqt olishi mumkin."
        )

        # Adminga xabar yuborish
        await notify_admins_about_payment(context, payment_request)


async def notify_admins_about_payment(context: ContextTypes.DEFAULT_TYPE, payment_request):
    """Adminlarga to'lov haqida xabar yuborish"""
    with app.app_context():
        user = User.query.get(payment_request.user_id)

        message = f"""
💳 Yangi to'lov so'rovi!

👤 Foydalanuvchi: {user.username or user.telegram_id}
📦 Tarif: {payment_request.tariff_name}
💰 Summa: {payment_request.amount:,} so'm
📝 Xabar: {payment_request.receipt_message}

ID: {payment_request.id}
"""

        keyboard = [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_approve_{payment_request.id}"),
                InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{payment_request.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        for admin_id in Config.ADMIN_TELEGRAM_IDS:
            if admin_id:
                try:
                    await context.bot.send_photo(
                        chat_id=int(admin_id),
                        photo=payment_request.receipt_file_id,
                        caption=message,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error sending to admin {admin_id}: {e}")


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin tugmalarini qayta ishlash"""
    query = update.callback_query
    await query.answer()

    data = query.data
    action, payment_id = data.replace('admin_', '').split('_')

    with app.app_context():
        admin_user = User.query.filter_by(telegram_id=query.from_user.id).first()

        if not admin_user or not admin_user.is_admin:
            await query.edit_message_caption(
                caption="❌ Siz admin emassiz!"
            )
            return

        payment_request = PaymentRequest.query.get(int(payment_id))

        if not payment_request:
            await query.edit_message_caption(
                caption="❌ To'lov topilmadi!"
            )
            return

        if action == 'approve':
            tariff = payment_request.approve(admin_user.id)
            await query.edit_message_caption(
                caption=f"✅ To'lov tasdiqlandi!\n\n{query.message.caption}"
            )

            # Foydalanuvchiga xabar yuborish
            user = User.query.get(payment_request.user_id)
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text=f"""
✅ To'lovingiz tasdiqlandi!

📦 Tarif: {tariff.tariff_name}
📊 So'rovlar: {tariff.requests_count} ta
⏳ Muddati: {tariff.duration_days} kun
⭐ TOP: {tariff.top_duration_days} kun

Mini App orqali e'loningizni faollashtirishingiz mumkin.
"""
            )

        elif action == 'reject':
            payment_request.reject(admin_user.id, "Admin tomonidan rad etildi")
            await query.edit_message_caption(
                caption=f"❌ To'lov rad etildi!\n\n{query.message.caption}"
            )

            # Foydalanuvchiga xabar yuborish
            user = User.query.get(payment_request.user_id)
            await context.bot.send_message(
                chat_id=user.telegram_id,
                text="❌ To'lovingiz rad etildi.\n\n"
                     "Iltimos, qaytadan to'g'ri chekni yuboring yoki qo'llab-quvvatlash xizmatiga murojaat qiling."
            )


async def send_notification(telegram_id: int, message: str, context: ContextTypes.DEFAULT_TYPE = None):
    """Foydalanuvchiga bildirishnoma yuborish"""
    if not context:
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        bot = application.bot
    else:
        bot = context.bot

    try:
        await bot.send_message(chat_id=telegram_id, text=message)
        return True
    except Exception as e:
        logger.error(f"Error sending notification to {telegram_id}: {e}")
        return False


# Flask app uchun global o'zgaruvchi
app = None


def set_flask_app(flask_app):
    """Flask app'ni o'rnatish"""
    global app
    app = flask_app
