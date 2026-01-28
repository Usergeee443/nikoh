from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import Config
from database import db
from models import User, PaymentRequest
import logging
import io
import asyncio

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
    command_args = context.args
    
    # Payment request ID bilan kelgan bo'lsa
    if command_args and command_args[0].startswith('payment_'):
        payment_id = command_args[0].replace('payment_', '')
        try:
            payment_id = int(payment_id)
            with app.app_context():
                payment_request = PaymentRequest.query.get(payment_id)
                if payment_request and payment_request.user.telegram_id == telegram_user.id:
                    await update.message.reply_text(
                        f"✅ To'lov so'rovi topildi!\n\n"
                        f"📦 Tarif: {payment_request.tariff_name}\n"
                        f"💰 Summa: {payment_request.amount:,} so'm\n\n"
                        f"📸 To'lov chekini rasm sifatida yuboring."
                    )
                    return
        except ValueError:
            pass
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

        # Foydalanuvchining pending to'lov so'rovini topish
        payment_request = PaymentRequest.query.filter_by(
            user_id=user.id,
            status='pending'
        ).order_by(PaymentRequest.created_at.desc()).first()

        if not payment_request:
            await update.message.reply_text(
                "❌ To'lov so'rovi topilmadi.\n\n"
                "Iltimos, avval tarifni tanlang va to'lov so'rovini yarating."
            )
            return

        # To'lov chekini yangilash
        payment_request.receipt_file_id = photo.file_id
        if caption:
            payment_request.receipt_message = caption
        db.session.commit()

        await update.message.reply_text(
            "✅ To'lov cheki qabul qilindi!\n\n"
            f"📦 Tarif: {payment_request.tariff_name}\n"
            f"💰 Summa: {payment_request.amount:,} so'm\n\n"
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
                    admin_id_int = int(admin_id.strip())
                    await context.bot.send_message(
                        chat_id=admin_id_int,
                        text=message,
                        reply_markup=reply_markup
                    )
                    
                    # Agar rasm bo'lsa, uni ham yuborish
                    if payment_request.receipt_file_id:
                        await context.bot.send_photo(
                            chat_id=admin_id_int,
                            photo=payment_request.receipt_file_id,
                            caption=f"To'lov cheki - ID: {payment_request.id}"
                        )
                except Exception as e:
                    logger.error(f"Error sending to admin {admin_id}: {e}")


def send_payment_receipt_to_admin(payment_request_id, image_data, image_filename, flask_app=None):
    """Web ilovadan yuborilgan to'lov chekini adminga yuborish"""
    import asyncio
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    
    # Flask app ni olish
    flask_app = flask_app or app
    if not flask_app:
        logger.error("Flask app context not available")
        return
    
    async def _send():
        try:
            bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
            
            with flask_app.app_context():
                payment_request = PaymentRequest.query.get(payment_request_id)
                if not payment_request:
                    logger.error(f"Payment request {payment_request_id} not found")
                    return
                
                user = User.query.get(payment_request.user_id)
                if not user:
                    logger.error(f"User not found for payment request {payment_request_id}")
                    return
                
                receipt_msg = payment_request.receipt_message or "Yo'q"
                message = f"""
💳 Yangi to'lov so'rovi (Web ilova)!

👤 Foydalanuvchi: {user.username or user.telegram_id}
📦 Tarif: {payment_request.tariff_name}
💰 Summa: {payment_request.amount:,} so'm
📝 Xabar: {receipt_msg}

ID: {payment_request.id}
"""

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_approve_{payment_request.id}"),
                        InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{payment_request.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Adminlarga rasm va xabar yuborish
                file_id = None
                admin_ids = Config.ADMIN_TELEGRAM_IDS
                
                if not admin_ids or (isinstance(admin_ids, list) and len(admin_ids) == 0):
                    logger.warning("No admin IDs configured")
                    return
                
                for admin_id_str in admin_ids:
                    if admin_id_str and admin_id_str.strip():
                        try:
                            admin_id = int(admin_id_str.strip())
                            
                            # Rasmni yuborish
                            photo_file = io.BytesIO(image_data)
                            photo_file.name = image_filename or 'receipt.jpg'
                            
                            logger.info(f"Sending receipt to admin {admin_id}")
                            sent_message = await bot.send_photo(
                                chat_id=admin_id,
                                photo=photo_file,
                                caption=message,
                                reply_markup=reply_markup
                            )
                            
                            logger.info(f"Receipt sent successfully to admin {admin_id}")
                            
                            # Birinchi marta yuborilganda file_id ni saqlash
                            if sent_message.photo and not file_id:
                                file_id = sent_message.photo[-1].file_id
                                logger.info(f"File ID saved: {file_id}")
                        except Exception as e:
                            logger.error(f"Error sending receipt to admin {admin_id_str}: {e}")
                            import traceback
                            traceback.print_exc()
                
                # File_id ni saqlash
                if file_id:
                    payment_request.receipt_file_id = file_id
                    db.session.commit()
                    logger.info(f"Payment request {payment_request_id} updated with file_id")
        except Exception as e:
            logger.error(f"Error in _send: {e}")
            import traceback
            traceback.print_exc()
    
    # Asyncio loop yaratish va ishga tushirish
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(_send())
    except Exception as e:
        logger.error(f"Error running async function: {e}")
        import traceback
        traceback.print_exc()


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin tugmalarini qayta ishlash"""
    query = update.callback_query
    await query.answer()

    data = query.data
    action, payment_id = data.replace('admin_', '').split('_')

    with app.app_context():
        admin_user = User.query.filter_by(telegram_id=query.from_user.id).first()
        
        # Admin tekshiruvi: is_admin=True yoki ADMIN_TELEGRAM_IDS ro'yxatida bo'lishi kerak
        is_admin = False
        if admin_user:
            is_admin = admin_user.is_admin
        
        # Agar is_admin=False bo'lsa, ADMIN_TELEGRAM_IDS ro'yxatini tekshirish
        if not is_admin:
            admin_telegram_id = str(query.from_user.id)
            if admin_telegram_id in Config.ADMIN_TELEGRAM_IDS:
                is_admin = True
                # Avtomatik admin qilish
                if admin_user:
                    admin_user.is_admin = True
                    db.session.commit()
                    logger.info(f"User {admin_user.telegram_id} automatically set as admin")

        if not is_admin:
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
