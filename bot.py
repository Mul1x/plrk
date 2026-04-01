import asyncio
import logging
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaVideo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, BOT_USERNAME, SUPER_ADMIN_IDS
from database import db
from states import DealStates, RequisitesStates, ScamStates, WithdrawStates, AdminStates, PaymentStates
from keyboards import (
    main_menu,
    lang_menu,
    deal_type_menu,
    currency_menu,
    requisites_edit_menu,
    scam_base_menu,
    back_menu,
    deal_buyer_menu,
    deal_seller_menu,
)
from utils import format_amount, get_rating_stars, t, escape_html

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

# Рандомный кошелек гаранта (для демонстрации)
GUARANTOR_WALLETS = [
    "UQA1478ВГ472О95-S7465HSAL234KD195HYD6_148GH-1",
    "UQA1478ВГ472О95-S7465HSAL234KD195HYD6_148GH-1",
    "UQA1478ВГ472О95-S7465HSAL234KD195HYD6_148GH-1",
    "UQA1478ВГ472О95-S7465HSAL234KD195HYD6_148GH-1",
]

def get_random_wallet() -> str:
    return random.choice(GUARANTOR_WALLETS)

async def send_video_menu(target, user_id: int, username: str, first_name: str):
    """Отправляет меню с видео"""
    user_data = db.get_user(user_id)
    rating = user_data[7] if user_data else 5.0
    deals_count = user_data[5] if user_data else 0
    stats = db.get_stats()
    total_paid = stats[1] if stats else 0
    lang = db.get_user_lang(user_id)
    
    is_super = user_id in SUPER_ADMIN_IDS
    markup = main_menu(is_super_admin=is_super, lang=lang)

    text = t('main_menu', lang).format(
        name=first_name,
        rating=get_rating_stars(rating),
        val=f"{rating:.1f}",
        deals=deals_count,
        total=format_amount(total_paid)
    )

    try:
        video = FSInputFile("main.mp4")
        if isinstance(target, Message):
            await target.answer_video(
                video=video, caption=text, parse_mode="HTML", reply_markup=markup
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer_video(
                video=video, caption=text, parse_mode="HTML", reply_markup=markup
            )
            try:
                await target.message.delete()
            except:
                pass
    except Exception as e:
        logger.error(f"Error sending video menu: {e}")
        if isinstance(target, Message):
            await target.answer(
                text=text, parse_mode="HTML", reply_markup=markup
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer(
                text=text, parse_mode="HTML", reply_markup=markup
            )
            try:
                await target.message.delete()
            except:
                pass

async def send_video_message(target, text: str, markup=None, parse_mode="HTML"):
    """Универсальная функция отправки сообщений с видео"""
    try:
        video = FSInputFile("main.mp4")
        if isinstance(target, Message):
            await target.answer_video(
                video=video, caption=text, parse_mode=parse_mode, reply_markup=markup
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer_video(
                video=video, caption=text, parse_mode=parse_mode, reply_markup=markup
            )
            try:
                await target.message.delete()
            except:
                pass
    except Exception as e:
        logger.error(f"Error sending video message: {e}")
        if isinstance(target, Message):
            await target.answer(
                text=text, parse_mode=parse_mode, reply_markup=markup
            )
        elif isinstance(target, CallbackQuery):
            await target.message.answer(
                text=text, parse_mode=parse_mode, reply_markup=markup
            )
            try:
                await target.message.delete()
            except:
                pass

# ==================== ОБРАБОТЧИКИ ====================

dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, bot: Bot):
    user = message.from_user
    db.save_user(user.id, user.username or "", user.first_name)

    if command.args:
        deal_id = command.args.replace("deal_", "")
        deal = db.get_deal(deal_id)

        if deal and deal["status"] == "waiting":
            # Проверяем, не присоединялся ли уже покупатель
            if deal.get("buyer_id"):
                # Если покупатель уже присоединен, но это тот же пользователь - пусть заходит
                if deal["buyer_id"] == user.id:
                    # Открываем сделку для уже присоединенного покупателя
                    amount_str = format_amount(deal["amount"])
                    seller = db.get_user(deal["seller_id"])
                    secret_code = deal.get("secret_code", f"{random.randint(100000, 999999)}")
                    
                    buyer_text = f"""
🔐 <b>СДЕЛКА #{deal["deal_id"]}</b>

👤 <b>Продавец:</b> {escape_html(seller[2] if seller else "Пользователь")}
📦 <b>Товар:</b> {escape_html(deal["description"])}
💰 <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

<b>💳 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ (ГАРАНТ):</b>
<code>{get_random_wallet()}</code>

<b>🔑 СЕКРЕТНЫЙ КЛЮЧ СДЕЛКИ:</b>
<code>{secret_code}</code>

<i>⚠️ Внимание! После оплаты нажмите кнопку "Я ОПЛАТИЛ" для подтверждения.</i>
<i>🔐 Секретный ключ потребуется при возникновении спора.</i>
"""
                    all_admins = SUPER_ADMIN_IDS + db.get_admins()
                    is_admin = user.id in all_admins
                    
                    await send_video_message(message, buyer_text, deal_buyer_menu(deal_id, is_admin))
                    return
                else:
                    await message.answer("❌ К этой сделке уже присоединился другой покупатель!")
                    await send_video_menu(message, user.id, user.username or "", user.first_name)
                    return
            
            # Проверка: нельзя присоединиться к своей сделке
            if deal["seller_id"] == user.id:
                await message.answer("❌ Вы не можете присоединиться к собственной сделке!")
                await send_video_menu(message, user.id, user.username or "", user.first_name)
                return
            
            # Присоединяем покупателя
            db.set_buyer(deal_id, user.id)
            deal = db.get_deal(deal_id)
            amount_str = format_amount(deal["amount"])
            seller = db.get_user(deal["seller_id"])
            
            # Получаем секретный код из базы
            secret_code = deal.get("secret_code", f"{random.randint(100000, 999999)}")
            
            # Текст для покупателя (с кошельком гаранта)
            buyer_text = f"""
🔐 <b>СДЕЛКА #{deal["deal_id"]}</b>

👤 <b>Продавец:</b> {escape_html(seller[2] if seller else "Пользователь")}
📦 <b>Товар:</b> {escape_html(deal["description"])}
💰 <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

<b>💳 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ (ГАРАНТ):</b>
<code>{get_random_wallet()}</code>

<b>🔑 СЕКРЕТНЫЙ КЛЮЧ СДЕЛКИ:</b>
<code>{secret_code}</code>

<i>⚠️ Внимание! После оплаты нажмите кнопку "Я ОПЛАТИЛ" для подтверждения.</i>
<i>🔐 Секретный ключ потребуется при возникновении спора.</i>
"""
            
            all_admins = SUPER_ADMIN_IDS + db.get_admins()
            is_admin = user.id in all_admins
            
            await send_video_message(message, buyer_text, deal_buyer_menu(deal_id, is_admin))
            
            # Уведомляем продавца
            seller_text = f"""
👥 <b>Покупатель присоединился к сделке #{deal["deal_id"]}</b>

👤 <b>Покупатель:</b> {escape_html(user.first_name)} @{escape_html(user.username or "нет")}
📦 <b>Товар:</b> {escape_html(deal["description"])}
💰 <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

<i>Ожидайте подтверждение оплаты от покупателя.</i>
<b>⚠️ Внимание! Убедитесь что имя покупателя присоединившегося к сделке совпадает с именем человека с которым вы договорились о сделке!</b>
"""
            await bot.send_message(
                deal["seller_id"],
                seller_text,
                parse_mode="HTML",
                reply_markup=deal_seller_menu(deal_id)
            )
            return

    await send_video_menu(message, user.id, user.username or "", user.first_name)

@dp.callback_query(F.data == "new_deal")
async def new_deal_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = db.get_user_lang(user_id)
    
    # Проверяем наличие реквизитов перед созданием сделки
    if not db.has_requisites(user_id):
        await callback.answer("⚠️ Сначала заполните реквизиты для вывода!", show_alert=True)
        await send_video_message(
            callback,
            "💳 <b>У вас не заполнены реквизиты!</b>\n\nДля создания сделки необходимо указать хотя бы один способ вывода средств.\n\nПожалуйста, выберите тип реквизитов для заполнения:",
            requisites_edit_menu()
        )
        return
    
    await callback.answer()
    await send_video_message(
        callback,
        t('select_type', lang),
        deal_type_menu(lang=lang)
    )
    await state.set_state(DealStates.waiting_deal_type)

@dp.callback_query(F.data == "restore_deal")
async def restore_deal_handler(callback: CallbackQuery, state: FSMContext):
    """Восстановление старой сделки"""
    lang = db.get_user_lang(callback.from_user.id)
    await callback.answer()
    
    text = """
🔄 <b>Восстановление сделки</b>

🙏 <b>Приносим извинения за неудобства!</b>

Если у вас была незавершенная сделка в старом боте, вы можете восстановить её здесь.

📎 <b>Пожалуйста, вставьте ссылку на старую сделку:</b>

Пример: <code>https://t.me/GiftsOkBot?start=deal_123456</code>

<i>После ввода ссылки мы автоматически восстановим информацию о сделке.</i>
"""
    await send_video_message(callback, text, back_menu())
    await state.set_state(DealStates.waiting_restore_link)

@dp.message(DealStates.waiting_restore_link, F.text)
async def process_restore_deal(message: Message, state: FSMContext):
    """Обработка ссылки на восстановление сделки"""
    link = message.text.strip()
    
    # Демо-данные для восстановления (товар НЕ кликабельный)
    demo_deal = {
        "amount": 1800,
        "currency": "RUB",
        "item": "t.me/nft/PetSnake-179530",
        "status": "paid"
    }
    
    # Текст для продавца (как при подтверждении оплаты)
    seller_text = f"""
✅ <b>Сделка успешно восстановлена!</b>

💰 <b>Сумма:</b> {format_amount(demo_deal['amount'])} {demo_deal['currency']}

📦 <b>Товар:</b> <code>{demo_deal['item']}</code>

🎁 <b>Инструкция по передаче подарка:</b>

1️⃣ Передайте подарок гаранту: @PlayerokGarants
2️⃣ Передача подтверждается автоматически
3️⃣ После подтверждения средства зачислятся на баланс

<i>Если у вас возникли вопросы, обратитесь в поддержку.</i>
"""
    await send_video_message(message, seller_text, back_menu())
    await state.clear()

@dp.callback_query(F.data == "back_to_deal_type")
async def back_to_deal_type_handler(callback: CallbackQuery, state: FSMContext):
    lang = db.get_user_lang(callback.from_user.id)
    await callback.answer()
    await send_video_message(
        callback,
        t('select_type', lang),
        deal_type_menu(lang=lang)
    )
    await state.set_state(DealStates.waiting_deal_type)

@dp.callback_query(F.data == "lang_menu")
async def lang_menu_handler(callback: CallbackQuery):
    lang = db.get_user_lang(callback.from_user.id)
    await callback.answer()
    await send_video_message(
        callback,
        t('select_lang', lang),
        lang_menu(lang=lang)
    )

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_lang_handler(callback: CallbackQuery):
    lang = callback.data.split("_")[2]
    db.update_language(callback.from_user.id, lang)
    await callback.answer("Language updated!" if lang == 'en' else "Язык обновлён!")
    await send_video_message(
        callback,
        t('select_lang', lang),
        lang_menu(lang=lang)
    )

@dp.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    if not user_data:
        db.save_user(
            callback.from_user.id,
            callback.from_user.username or "",
            callback.from_user.first_name,
        )
        user_data = db.get_user(callback.from_user.id)

    rating = user_data[7]
    deals_count = user_data[5] + user_data[6]
    balance = user_data[3]
    frozen = user_data[4]

    text = f"""
👤 <b>Профиль пользователя</b>

<b>ID:</b> <code>{callback.from_user.id}</code>
<b>Имя:</b> {escape_html(callback.from_user.first_name)}
<b>Username:</b> @{escape_html(callback.from_user.username or "не указан")}

<b>Рейтинг:</b> {get_rating_stars(rating)} ({rating:.1f}/5)
<b>Всего сделок:</b> {deals_count}

💰 <b>Баланс:</b> {format_amount(balance)} RUB
❄️ <b>Заморожено:</b> {format_amount(frozen)} RUB
"""
    await callback.answer()
    await send_video_message(callback, text, back_menu())

@dp.callback_query(DealStates.waiting_deal_type, F.data.startswith("type_"))
async def deal_type_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    type_key = callback.data.split("_")[1]
    type_map = {"gift": "Подарок", "account": "Аккаунт", "other": "Другое"}
    deal_type = type_map.get(type_key, "Другое")
    await state.update_data(deal_type=deal_type)

    text = f"<b>Введите описание товара</b> (Тип: {escape_html(deal_type)}):"
    if deal_type == "Подарок":
        text += "\n\n<i>ВНИМАНИЕ! Для типа 'Подарок':\nПосле подтверждения оплаты вы должны передать подарок покупателю.</i>"

    await send_video_message(callback, text, back_menu())
    await state.set_state(DealStates.waiting_description)

@dp.message(DealStates.waiting_description, F.text)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=escape_html(message.text))
    await send_video_message(
        message,
        "<b>Введите сумму сделки:</b>\nПример: 15000",
        back_menu()
    )
    await state.set_state(DealStates.waiting_amount)

@dp.message(DealStates.waiting_amount, F.text)
async def get_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except:
        await send_video_message(
            message,
            "❌ Введите корректную сумму (положительное число):",
            back_menu()
        )
        return

    await state.update_data(amount=amount)
    lang = db.get_user_lang(message.from_user.id)
    await send_video_message(
        message,
        t('select_currency', lang).format(amount=format_amount(amount)),
        currency_menu()
    )
    await state.set_state(DealStates.waiting_currency)

@dp.callback_query(DealStates.waiting_currency, F.data.startswith("cur_"))
async def get_currency(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    currency = callback.data.split("_")[1]
    data = await state.get_data()
    deal_type = data.get("deal_type")
    description = data.get("description")
    amount = data.get("amount")
    lang = db.get_user_lang(callback.from_user.id)

    deal_id = db.create_deal(callback.from_user.id, deal_type, description, amount, currency)
    link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
    amount_str = format_amount(amount)

    # Текст для продавца (создателя сделки)
    seller_text = f"""
✅ <b>Сделка #{deal_id} создана!</b>

📦 <b>Тип:</b> {escape_html(deal_type)}
📋 <b>Товар:</b> {description}
💰 <b>Сумма:</b> {amount_str} {escape_html(currency)}

🔗 <b>Ссылка для приглашения покупателя:</b>
<code>{link}</code>

<i>⚠️ Отправьте эту ссылку покупателю для присоединения к сделке.</i>
<i>🔐 После присоединения покупателя вы получите уведомление.</i>
"""
    
    # Создаем кнопку для копирования ссылки
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Копировать ссылку", callback_data=f"copy_link_{deal_id}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu"))
    
    await send_video_message(callback, seller_text, builder.as_markup())
    await state.clear()

@dp.callback_query(F.data.startswith("copy_link_"))
async def copy_link_handler(callback: CallbackQuery):
    """Отправляет ссылку для копирования"""
    deal_id = callback.data.replace("copy_link_", "")
    link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
    
    await callback.answer()
    await callback.message.answer(
        f"🔗 <b>Ссылка для покупателя:</b>\n\n<code>{link}</code>\n\n<i>Отправьте её покупателю для присоединения к сделке.</i>",
        parse_mode="HTML",
        reply_markup=back_menu()
    )

@dp.callback_query(F.data == "requisites")
async def requisites_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    requisites = json.loads(user_data[8]) if user_data and user_data[8] else {}

    text = "💳 <b>Ваши реквизиты для вывода:</b>\n\n"
    type_names = {"card": "Карта", "kaspi": "Kaspi", "qiwi": "QIWI", "yoomoney": "ЮMoney", "webmoney": "WebMoney", "ton": "TON"}

    for req_type, name in type_names.items():
        val = requisites.get(req_type, "<i>не указано</i>")
        text += f"• <b>{name}:</b> {val}\n"

    text += "\nВыберите тип для изменения:"
    await callback.answer()
    await send_video_message(callback, text, requisites_edit_menu())

@dp.callback_query(F.data == "scam_base")
async def scam_base_handler(callback: CallbackQuery):
    await callback.answer()
    await send_video_message(callback, "Выберите действие:", scam_base_menu())

@dp.callback_query(F.data == "my_deals")
async def my_deals_handler(callback: CallbackQuery):
    deals = db.get_user_deals(callback.from_user.id)
    if not deals:
        await callback.answer()
        await send_video_message(callback, "📋 <b>У вас пока нет сделок</b>", back_menu())
        return

    text = "📋 <b>Ваши последние сделки:</b>\n\n"
    for deal in deals[:10]:
        status_emoji = "⏳" if deal[7] == "waiting" else "✅"
        text += f"{status_emoji} #{deal[0]} | {escape_html(deal[3])} | {format_amount(deal[5])} {deal[6]}\n"
        
        # Добавляем кнопку для входа в сделку
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔓 Войти в сделку", callback_data=f"enter_deal_{deal[0]}"))
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu"))
        
        await callback.answer()
        await send_video_message(callback, text, builder.as_markup())
        return

@dp.callback_query(F.data.startswith("enter_deal_"))
async def enter_deal_handler(callback: CallbackQuery):
    """Вход в существующую сделку из списка"""
    deal_id = callback.data.replace("enter_deal_", "")
    deal = db.get_deal(deal_id)
    user = callback.from_user
    
    if not deal:
        await callback.answer("Сделка не найдена!")
        return
    
    if deal["status"] != "waiting":
        await callback.answer("Сделка уже завершена!")
        return
    
    amount_str = format_amount(deal["amount"])
    seller = db.get_user(deal["seller_id"])
    secret_code = deal.get("secret_code", f"{random.randint(100000, 999999)}")
    
    # Если пользователь - продавец
    if deal["seller_id"] == user.id:
        buyer = db.get_user(deal["buyer_id"]) if deal.get("buyer_id") else None
        text = f"""
📋 <b>СДЕЛКА #{deal_id}</b>

📦 <b>Товар:</b> {escape_html(deal["description"])}
💰 <b>Сумма:</b> {amount_str} {deal["currency"]}
👤 <b>Покупатель:</b> {escape_html(buyer[2] if buyer else "Не присоединился")}
📊 <b>Статус:</b> {"🟡 Ожидает оплаты" if deal["status"] == "waiting" else "✅ Оплачено"}
"""
        await send_video_message(callback, text, deal_seller_menu(deal_id))
        return
    
    # Если пользователь - покупатель или еще не присоединился
    if deal.get("buyer_id") and deal["buyer_id"] != user.id:
        await callback.answer("❌ К этой сделке уже присоединился другой покупатель!")
        return
    
    # Если покупатель еще не присоединен, присоединяем
    if not deal.get("buyer_id"):
        db.set_buyer(deal_id, user.id)
        deal = db.get_deal(deal_id)
        
        # Уведомляем продавца
        await callback.bot.send_message(
            deal["seller_id"],
            f"👥 <b>Покупатель присоединился к сделке #{deal_id}</b>\n\n👤 {escape_html(user.first_name)} @{escape_html(user.username or 'нет')}",
            parse_mode="HTML"
        )
    
    # Открываем сделку для покупателя
    buyer_text = f"""
🔐 <b>СДЕЛКА #{deal_id}</b>

👤 <b>Продавец:</b> {escape_html(seller[2] if seller else "Пользователь")}
📦 <b>Товар:</b> {escape_html(deal["description"])}
💰 <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

<b>💳 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ (ГАРАНТ):</b>
<code>{get_random_wallet()}</code>

<b>🔑 СЕКРЕТНЫЙ КЛЮЧ СДЕЛКИ:</b>
<code>{secret_code}</code>

<i>⚠️ Внимание! После оплаты нажмите кнопку "Я ОПЛАТИЛ" для подтверждения.</i>
"""
    all_admins = SUPER_ADMIN_IDS + db.get_admins()
    is_admin = user.id in all_admins
    
    await send_video_message(callback, buyer_text, deal_buyer_menu(deal_id, is_admin))

@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    available = user_data[3] if user_data else 0

    text = f"""
💰 <b>Вывод средств</b>

<b>Доступно для вывода:</b> {format_amount(available)} RUB
<b>Минимальная сумма:</b> 100 RUB

Для вывода средств у вас должны быть заполнены реквизиты.
"""
    if available > 0:
        text += "\n✏️ Введите сумму для вывода:"

    await callback.answer()
    await send_video_message(callback, text, back_menu())

@dp.callback_query(F.data.startswith("req_"))
async def requisites_edit_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    req_type = callback.data[4:]
    type_names = {"card": "Карта", "kaspi": "Kaspi", "qiwi": "QIWI", "yoomoney": "ЮMoney", "webmoney": "WebMoney", "ton": "TON"}
    await state.update_data(req_type=req_type)
    await send_video_message(
        callback,
        f"<b>{type_names[req_type]}</b>\n\nВведите реквизиты:",
        back_menu()
    )
    await state.set_state(RequisitesStates.waiting_value)

@dp.message(RequisitesStates.waiting_value, F.text)
async def get_requisite_value(message: Message, state: FSMContext):
    data = await state.get_data()
    req_type = data.get("req_type")
    db.update_requisites(message.from_user.id, req_type, escape_html(message.text))
    await send_video_message(message, "✅ Реквизиты сохранены!", back_menu())
    await state.clear()

# ==================== НОВЫЕ ХЕНДЛЕРЫ СДЕЛОК ====================

@dp.callback_query(F.data.startswith("fake_pay_"))
async def fake_pay_handler(callback: CallbackQuery):
    """Обработчик фейковой оплаты для обычных пользователей"""
    await callback.answer("❌ Оплата не найдена! Пожалуйста, проверьте реквизиты и попробуйте снова.", show_alert=True)

@dp.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment_handler(callback: CallbackQuery, bot: Bot):
    """Реальное подтверждение оплаты для админов"""
    all_admins = SUPER_ADMIN_IDS + db.get_admins()
    if callback.from_user.id not in all_admins:
        return await callback.answer("У вас нет прав для подтверждения оплаты!", show_alert=True)
    
    await callback.answer()
    deal_id = callback.data.replace("confirm_payment_", "")
    deal = db.get_deal(deal_id)
    
    if not deal or deal["status"] != "waiting":
        await callback.answer("Сделка уже завершена или не существует!")
        return
    
    db.mark_paid(deal_id)
    amount_str = format_amount(deal["amount"])
    
    # Уведомляем продавца с инструкцией (как при восстановлении)
    seller_text = f"""
✅ <b>Оплата по сделке #{deal_id} подтверждена!</b>

💰 <b>Сумма:</b> {amount_str} {deal['currency']}

📦 <b>Товар:</b> {escape_html(deal["description"])}

🎁 <b>Инструкция по передаче подарка:</b>

1️⃣ Передайте подарок гаранту: @PlayerokGarants
2️⃣ Передача подтверждается автоматически
3️⃣ После подтверждения средства зачислятся на баланс

<i>Если у вас возникли вопросы, обратитесь в поддержку.</i>
"""
    await bot.send_message(
        deal["seller_id"],
        seller_text,
        parse_mode="HTML"
    )
    
    # Уведомляем покупателя
    if deal.get("buyer_id"):
        await bot.send_message(
            deal["buyer_id"],
            f"✅ <b>Ваша оплата по сделке #{deal_id} подтверждена!</b>\n\n<i>Ожидайте получение товара от продавца.</i>",
            parse_mode="HTML"
        )
    
    await callback.message.edit_text(
        f"✅ <b>Оплата по сделке #{deal_id} подтверждена!</b>",
        parse_mode="HTML",
        reply_markup=back_menu()
    )

@dp.callback_query(F.data.startswith("exit_deal_"))
async def exit_deal_handler(callback: CallbackQuery, bot: Bot):
    """Выход из сделки"""
    await callback.answer()
    deal_id = callback.data.replace("exit_deal_", "")
    deal = db.get_deal(deal_id)
    
    if not deal:
        await callback.message.answer("Сделка не найдена!")
        return
    
    if deal["status"] != "waiting":
        await callback.answer("Сделка уже завершена, выход невозможен!")
        return
    
    # Очищаем покупателя из сделки
    db.clear_buyer(deal_id)
    
    # Уведомляем продавца
    await bot.send_message(
        deal["seller_id"],
        f"🚪 <b>Покупатель вышел из сделки #{deal_id}</b>\n\n👤 {escape_html(callback.from_user.first_name)} @{escape_html(callback.from_user.username or 'нет')}\n\n<i>Вы можете создать новую сделку.</i>",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        "🚪 Вы вышли из сделки.",
        reply_markup=back_menu()
    )

@dp.callback_query(F.data.startswith("view_deal_"))
async def view_deal_handler(callback: CallbackQuery):
    """Просмотр сделки для продавца"""
    deal_id = callback.data.replace("view_deal_", "")
    deal = db.get_deal(deal_id)
    
    if not deal:
        await callback.answer("Сделка не найдена!")
        return
    
    buyer = db.get_user(deal["buyer_id"]) if deal.get("buyer_id") else None
    amount_str = format_amount(deal["amount"])
    
    text = f"""
📋 <b>СДЕЛКА #{deal_id}</b>

📦 <b>Товар:</b> {escape_html(deal["description"])}
💰 <b>Сумма:</b> {amount_str} {deal["currency"]}
👤 <b>Покупатель:</b> {escape_html(buyer[2] if buyer else "Не присоединился")}
📊 <b>Статус:</b> {"🟡 Ожидает оплаты" if deal["status"] == "waiting" else "✅ Оплачено"}
"""
    
    await send_video_message(callback, text, back_menu())

@dp.callback_query(F.data == "menu")
async def menu_handler(callback: CallbackQuery):
    await callback.answer()
    await send_video_menu(callback, callback.from_user.id, callback.from_user.username or "", callback.from_user.first_name)

# ==================== АДМИН ПАНЕЛЬ ====================

@dp.callback_query(F.data == "admin_list")
async def admin_list_handler(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    admins = db.get_admins()
    text = "👥 <b>Список обычных администраторов:</b>\n\n"
    if not admins:
        text += "<i>Список пуст</i>"
    else:
        for i, admin_id in enumerate(admins, 1):
            text += f"{i}. <code>{admin_id}</code>\n"
    
    await send_video_message(callback, text, back_menu())

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    await send_video_message(
        callback,
        "Введите Telegram ID пользователя, которого хотите сделать админом:",
        back_menu()
    )
    await state.set_state(AdminStates.waiting_admin_id_add)

@dp.message(AdminStates.waiting_admin_id_add, F.text)
async def admin_add_finish(message: Message, state: FSMContext):
    if message.from_user.id not in SUPER_ADMIN_IDS:
        return
    
    try:
        admin_id = int(message.text)
        db.add_admin(admin_id)
        await send_video_message(
            message,
            f"✅ Пользователь <code>{admin_id}</code> назначен администратором!",
            back_menu()
        )
        await state.clear()
    except ValueError:
        await send_video_message(message, "❌ Введите корректный числовой ID!", back_menu())

@dp.callback_query(F.data == "admin_remove")
async def admin_remove_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    await send_video_message(
        callback,
        "Введите Telegram ID пользователя, которого хотите удалить из админов:",
        back_menu()
    )
    await state.set_state(AdminStates.waiting_admin_id_remove)

@dp.message(AdminStates.waiting_admin_id_remove, F.text)
async def admin_remove_finish(message: Message, state: FSMContext):
    if message.from_user.id not in SUPER_ADMIN_IDS:
        return
    
    try:
        admin_id = int(message.text)
        db.remove_admin(admin_id)
        await send_video_message(
            message,
            f"✅ Пользователь <code>{admin_id}</code> удален из списка администраторов!",
            back_menu()
        )
        await state.clear()
    except ValueError:
        await send_video_message(message, "❌ Введите корректный числовой ID!", back_menu())

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer("У вас нет прав!", show_alert=True)
    
    await send_video_message(
        callback,
        "Введите сообщение для рассылки всем пользователям:",
        back_menu()
    )
    await state.set_state(AdminStates.waiting_broadcast_msg)

@dp.message(AdminStates.waiting_broadcast_msg, F.text)
async def admin_broadcast_finish(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in SUPER_ADMIN_IDS:
        return
    
    users = db.get_all_users()
    count = 0
    await send_video_message(message, f"🚀 Начинаю рассылку на {len(users)} пользователей...")
    
    for user_id in users:
        try:
            await bot.send_message(user_id, message.text, parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await send_video_message(message, f"✅ Рассылка завершена! Получили: {count} пользователей.", back_menu())
    await state.clear()

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("✅ GIFT GUARD бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
