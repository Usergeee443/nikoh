from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import Config
from database import db
from models import User, PaymentRequest, Profile, Setting
from datetime import datetime
import logging
import io
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _is_admin(telegram_id):
    """Foydalanuvchi adminmi (ADMIN_TELEGRAM_IDS yoki User.is_admin)"""
    if str(telegram_id) in (Config.ADMIN_TELEGRAM_IDS or []):
        return True
    with app.app_context():
        u = User.query.filter_by(telegram_id=telegram_id).first()
        return u and u.is_admin


def setup_bot(app):
    """Telegram botni sozlash"""
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot will not start.")
        return None

    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("admin_add", admin_add_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_receipt))
    application.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r'^admin_'))

    return application


def _admin_site_url(telegram_id):
    """Admin uchun sayt linki (SITE_URL + /admin); Web App tugmasi bu URLni ochadi"""
    base = (getattr(Config, 'SITE_URL', None) or '').strip().rstrip('/')
    if not base:
        return ''
    path = f"{base}/admin"
    return f"{path}?user_id={telegram_id}" if telegram_id else path


# Eski nom (cache/restartda xato bo'lmasligi uchun)
_mini_app_url = _admin_site_url


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel — faqat adminlar uchun"""
    telegram_id = update.effective_user.id
    if not _is_admin(telegram_id):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.")
        return
    with app.app_context():
        pending_pay = PaymentRequest.query.filter_by(status='pending').count()
        pending_mod = Profile.query.filter(Profile.moderation_status == 'pending').count() if hasattr(Profile, 'moderation_status') else 0
    text = (
        "🔐 **Admin panel**\n\n"
        f"💳 To'lovlar kutilmoqda: {pending_pay}\n"
        f"📋 E'lonlar moderatsiyada: {pending_mod}\n\n"
        "Quyidagi tugmalardan birini tanlang:"
    )
    keyboard = [
        [InlineKeyboardButton("💳 To'lovlar", callback_data="admin_menu_payments")],
        [InlineKeyboardButton("📋 Moderatsiya (e'lonlar)", callback_data="admin_menu_moderation")],
        [InlineKeyboardButton("💰 Narxlar", callback_data="admin_menu_prices")],
        [InlineKeyboardButton("👤 Admin qo'shish", callback_data="admin_menu_add")],
    ]
    site_url = _admin_site_url(telegram_id)
    mini_url = (getattr(Config, 'MINI_APP_URL', None) or '').strip().rstrip('/')
    if site_url:
        keyboard.insert(0, [InlineKeyboardButton("🌐 Admin panel", web_app=WebAppInfo(url=site_url))])
    if mini_url:
        keyboard.insert(1, [InlineKeyboardButton("📱 Mini ilova (asosiy)", web_app=WebAppInfo(url=mini_url))])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def admin_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi admin qo'shish: /admin_add 123456789"""
    telegram_id = update.effective_user.id
    if not _is_admin(telegram_id):
        await update.message.reply_text("❌ Sizda admin huquqi yo'q.")
        return
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text("Iltimos, Telegram ID kiriting.\nMasalan: /admin_add 123456789")
        return
    try:
        new_tid = int(args[0])
    except ValueError:
        await update.message.reply_text("Telegram ID raqam bo'lishi kerak.")
        return
    with app.app_context():
        u = User.query.filter_by(telegram_id=new_tid).first()
        if not u:
            u = User(telegram_id=new_tid, is_admin=True)
            db.session.add(u)
            db.session.commit()
            await update.message.reply_text(f"✅ Yangi foydalanuvchi va admin qo'shildi: {new_tid}")
        else:
            u.is_admin = True
            db.session.commit()
            await update.message.reply_text(f"✅ Admin qo'shildi: {new_tid} (@{u.username or '-'})")


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
    """Web ilovadan yuborilgan to'lov chekini adminga yuborish (barcha tariflar: KUMUSH, OLTIN, VIP, TOP_*)"""
    import asyncio
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
    
    if not image_data or len(image_data) == 0:
        logger.error("send_payment_receipt_to_admin: image_data bo'sh, adminga yuborilmaydi")
        return
    
    flask_app = flask_app or app
    if not flask_app:
        logger.error("Flask app context not available")
        return
    
    logger.info(f"send_payment_receipt_to_admin: payment_request_id={payment_request_id}, image_size={len(image_data)}, filename={image_filename}")
    
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
                amount_val = payment_request.amount if payment_request.amount is not None else 0
                message = f"""
💳 Yangi to'lov so'rovi (Web ilova)!

👤 Foydalanuvchi: {user.username or user.telegram_id}
📦 Tarif: {payment_request.tariff_name}
💰 Summa: {amount_val:,} so'm
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
                
                admin_ids = [a for a in (admin_ids or []) if a]
                for admin_id_str in admin_ids:
                    try:
                        admin_id = int(str(admin_id_str).strip())
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
                        if sent_message.photo and not file_id:
                            file_id = sent_message.photo[-1].file_id
                            logger.info(f"File ID saved: {file_id}")
                    except (ValueError, Exception) as e:
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
    
    # Thread ichida asyncio.run() ishlatish (botga xabar yuborish)
    try:
        asyncio.run(_send())
    except Exception as e:
        logger.error(f"Error running async send_payment_receipt: {e}")
        import traceback
        traceback.print_exc()


def send_pending_listing_to_admins(profile_id, flask_app=None):
    """Yangi e'lon yaratilganda adminlarga xabar yuborish (moderatsiya kutilmoqda)"""
    import asyncio
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

    flask_app = flask_app or app
    if not flask_app:
        logger.error("send_pending_listing_to_admins: Flask app context yo'q")
        return

    async def _send():
        try:
            bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
            with flask_app.app_context():
                profile = Profile.query.get(profile_id)
                if not profile or getattr(profile, 'moderation_status', None) != 'pending':
                    return
                u = User.query.get(profile.user_id)
                author = (u.username or str(u.telegram_id) or '—') if u else '—'
                message = f"""
📋 **Yangi e'lon — moderatsiya kutilmoqda**

👤 Ism: {profile.name or '—'}
📌 Jins: {profile.gender or '—'}
📍 Hudud: {profile.region or '—'}
🆔 E'lon ID: {profile.id}
👤 Foydalanuvchi: {author}

Tasdiqlangandan keyin e'lon feedda ko'rinadi.
"""
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_mod_approve_{profile.id}"),
                        InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_mod_reject_{profile.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                admin_ids = Config.ADMIN_TELEGRAM_IDS or []
                for admin_id_str in admin_ids:
                    if not admin_id_str:
                        continue
                    try:
                        admin_id = int(str(admin_id_str).strip())
                        await bot.send_message(
                            chat_id=admin_id,
                            text=message,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"send_pending_listing_to_admins: admin {admin_id_str} ga yuborishda xato: {e}")
        except Exception as e:
            logger.error(f"send_pending_listing_to_admins: {e}")
            import traceback
            traceback.print_exc()

    try:
        asyncio.run(_send())
    except Exception as e:
        logger.error(f"send_pending_listing_to_admins run: {e}")


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin tugmalarini qayta ishlash: to'lovlar, moderatsiya, menyu"""
    query = update.callback_query
    await query.answer()
    data = query.data
    telegram_id = query.from_user.id

    with app.app_context():
        admin_user = User.query.filter_by(telegram_id=telegram_id).first()
        is_admin = bool(admin_user and admin_user.is_admin) or str(telegram_id) in (Config.ADMIN_TELEGRAM_IDS or [])
        if admin_user and str(telegram_id) in (Config.ADMIN_TELEGRAM_IDS or []):
            admin_user.is_admin = True
            db.session.commit()

        if not is_admin:
            try:
                await query.edit_message_text(text="❌ Siz admin emassiz!")
            except Exception:
                await query.edit_message_caption(caption="❌ Siz admin emassiz!")
            return

        # Admin menyu
        if data == "admin_menu_payments":
            pending = PaymentRequest.query.filter_by(status='pending').order_by(PaymentRequest.created_at.desc()).limit(15).all()
            if not pending:
                await query.edit_message_text(text="💳 Kutilayotgan to'lovlar yo'q.\n\n/admin — bosh menyu")
                return
            lines = ["💳 **Kutilayotgan to'lovlar:**\n"]
            for pr in pending:
                u = pr.user
                lines.append(f"ID {pr.id}: {u.username or pr.user_id} — {pr.tariff_name} {pr.amount:,} so'm")
            text = "\n".join(lines)[:4000]
            kb = []
            for pr in pending[:10]:
                kb.append([
                    InlineKeyboardButton(f"✅ {pr.id}", callback_data=f"admin_approve_{pr.id}"),
                    InlineKeyboardButton(f"❌ {pr.id}", callback_data=f"admin_reject_{pr.id}"),
                ])
            kb.append([InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu_back")])
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            return

        if data == "admin_menu_moderation":
            if not hasattr(Profile, 'moderation_status'):
                await query.edit_message_text(text="Moderatsiya moduli mavjud emas.")
                return
            pending = Profile.query.filter(Profile.moderation_status == 'pending').order_by(Profile.created_at.desc()).limit(15).all()
            if not pending:
                await query.edit_message_text(text="📋 Moderatsiyada e'lonlar yo'q.\n\n/admin — bosh menyu")
                return
            lines = ["📋 **Kutilayotgan e'lonlar:**\n"]
            for p in pending:
                lines.append(f"ID {p.id}: {p.name or '-'}, {p.gender}, {p.region or '-'}")
            text = "\n".join(lines)[:4000]
            kb = []
            for p in pending[:10]:
                kb.append([
                    InlineKeyboardButton(f"✅ {p.id}", callback_data=f"admin_mod_approve_{p.id}"),
                    InlineKeyboardButton(f"❌ {p.id}", callback_data=f"admin_mod_reject_{p.id}"),
                ])
            kb.append([InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu_back")])
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            return

        if data == "admin_menu_prices":
            def _p(k, d):
                v = Setting.get(k) if Setting else None
                if v is not None and v != '':
                    try:
                        return int(v)
                    except ValueError:
                        pass
                return d
            prices = {
                'KUMUSH': _p('KUMUSH_TARIFF_PRICE', getattr(Config, 'KUMUSH_TARIFF_PRICE', 50000)),
                'OLTIN': _p('OLTIN_TARIFF_PRICE', getattr(Config, 'OLTIN_TARIFF_PRICE', 100000)),
                'VIP': _p('VIP_TARIFF_PRICE', getattr(Config, 'VIP_TARIFF_PRICE', 250000)),
                'TOP 7': _p('TOP_7_PRICE', 15000),
                'TOP 30': _p('TOP_30_PRICE', 30000),
            }
            text = "💰 **Tarif narxlari (so'm):**\n\n" + "\n".join(f"{k}: {v:,}" + (" (bepul)" if v == 0 else "") for k, v in prices.items())
            text += "\n\nNarxlarni o'zgartirish yoki bepul qilish uchun Admin panel (veb) dan foydalaning."
            kb = [[InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu_back")]]
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
            return

        if data == "admin_menu_add":
            await query.edit_message_text(
                text="👤 **Yangi admin qo'shish**\n\n"
                     "Telegram ID ni quyidagi ko'rinishda yuboring:\n"
                     "`/admin_add 123456789`\n\n"
                     "(Foydalanuvchi avval botda /start bosgan bo'lishi kerak.)",
                parse_mode='Markdown'
            )
            return

        if data == "admin_menu_back":
            pending_pay = PaymentRequest.query.filter_by(status='pending').count()
            pending_mod = Profile.query.filter(Profile.moderation_status == 'pending').count() if hasattr(Profile, 'moderation_status') else 0
            text = (
                "🔐 **Admin panel**\n\n"
                f"💳 To'lovlar kutilmoqda: {pending_pay}\n"
                f"📋 E'lonlar moderatsiyada: {pending_mod}\n\n"
                "Quyidagi tugmalardan birini tanlang:"
            )
            keyboard = [
                [InlineKeyboardButton("💳 To'lovlar", callback_data="admin_menu_payments")],
                [InlineKeyboardButton("📋 Moderatsiya (e'lonlar)", callback_data="admin_menu_moderation")],
                [InlineKeyboardButton("💰 Narxlar", callback_data="admin_menu_prices")],
                [InlineKeyboardButton("👤 Admin qo'shish", callback_data="admin_menu_add")],
            ]
            site_url = _admin_site_url(telegram_id)
            if site_url:
                keyboard.insert(0, [InlineKeyboardButton("📱 Mini ilovani ochish", web_app=WebAppInfo(url=site_url))])
            await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return

        # To'lov: admin_approve_<id>, admin_reject_<id>
        if data.startswith("admin_approve_") or data.startswith("admin_reject_"):
            part = data.replace("admin_", "", 1)
            action, pid = part.split("_", 1)
            payment_id = int(pid)
            payment_request = PaymentRequest.query.get(payment_id)
            if not payment_request:
                await query.edit_message_text(text="❌ To'lov topilmadi!")
                return
            if payment_request.status != 'pending':
                await query.edit_message_text(text="❌ Bu to'lov allaqachon qayta ishlangan.")
                return
            if action == 'approve':
                tariff = payment_request.approve(admin_user.id)
                try:
                    await query.edit_message_text(text=f"✅ To'lov tasdiqlandi! ID: {payment_id}")
                except Exception:
                    await query.edit_message_caption(caption=f"✅ To'lov tasdiqlandi! ID: {payment_id}")
                user = User.query.get(payment_request.user_id)
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=f"✅ To'lovingiz tasdiqlandi!\n📦 Tarif: {tariff.tariff_name}\n📊 So'rovlar: {tariff.requests_count} ta\n⏳ Muddati: {tariff.duration_days} kun\n⭐ TOP: {tariff.top_duration_days} kun\n\nMini App orqali e'loningizni faollashtirishingiz mumkin."
                )
            else:
                payment_request.reject(admin_user.id, "Admin tomonidan rad etildi")
                try:
                    await query.edit_message_text(text=f"❌ To'lov rad etildi. ID: {payment_id}")
                except Exception:
                    await query.edit_message_caption(caption=f"❌ To'lov rad etildi. ID: {payment_id}")
                user = User.query.get(payment_request.user_id)
                await context.bot.send_message(chat_id=user.telegram_id, text="❌ To'lovingiz rad etildi.\n\nIltimos, qaytadan to'g'ri chekni yuboring yoki qo'llab-quvvatlash xizmatiga murojaat qiling.")
            return

        # Moderatsiya: admin_mod_approve_<id>, admin_mod_reject_<id>
        if data.startswith("admin_mod_approve_") or data.startswith("admin_mod_reject_"):
            part = data.replace("admin_mod_", "", 1)
            action, pid = part.split("_", 1)
            profile_id = int(pid)
            profile = Profile.query.get(profile_id)
            if not profile or getattr(profile, 'moderation_status', None) != 'pending':
                await query.edit_message_text(text="❌ E'lon topilmadi yoki allaqachon ko'rib chiqilgan.")
                return
            if action == 'approve':
                profile.moderation_status = 'approved'
                profile.is_active = True
                if not profile.activated_at:
                    profile.activated_at = datetime.utcnow()
                db.session.commit()
                await query.edit_message_text(text=f"✅ E'lon tasdiqlandi! ID: {profile_id}")
            else:
                profile.moderation_status = 'rejected'
                profile.is_active = False
                db.session.commit()
                await query.edit_message_text(text=f"❌ E'lon rad etildi. ID: {profile_id}")
            return


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


def send_notification_sync(telegram_id: int, message: str):
    """Flask/thread dan chaqirish uchun: foydalanuvchiga xabar yuborish (sinxron wrapper)"""
    if not telegram_id:
        return False
    try:
        asyncio.run(send_notification(telegram_id, message))
        return True
    except Exception as e:
        logger.error(f"send_notification_sync to {telegram_id}: {e}")
        return False


# Flask app uchun global o'zgaruvchi
app = None


def set_flask_app(flask_app):
    """Flask app'ni o'rnatish"""
    global app
    app = flask_app
