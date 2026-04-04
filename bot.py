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
    LabeledPrice,
    PreCheckoutQuery,
    SuccessfulPayment,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, BOT_USERNAME, SUPER_ADMIN_IDS
from database import db
from states import DealStates, RequisitesStates, WithdrawStates, AdminStates, SubscriptionStates
from keyboards import (
    main_menu,
    admin_panel_menu,
    lang_menu,
    deal_type_menu,
    currency_menu,
    requisites_edit_menu,
    back_menu,
    deal_buyer_menu,
    deal_seller_menu,
    subscription_menu,
    my_subscriptions_menu,
)
from utils import format_amount, get_rating_stars, t, escape_html
from premium_emoji import get_emoji, replace_emojis_in_text

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

# Рандомный кошелек гаранта (для демонстрации)
GUARANTOR_WALLETS = [
    "UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "EQD__________________________________________",
    "UQB__________________________________________",
    "EQC__________________________________________",
]

def get_random_wallet() -> str:
    return random.choice(GUARANTOR_WALLETS)

async def send_video_menu(target, user_id: int, username: str, first_name: str):
    """Отправляет меню с видео"""
    # Проверяем и деактивируем истекшие подписки
    db.deactivate_expired_subscriptions()
    
    user_data = db.get_user(user_id)
    rating = user_data[7] if user_data else 5.0
    lang = db.get_user_lang(user_id)
    
    is_super = user_id in SUPER_ADMIN_IDS
    has_subscription = db.is_premium_subscriber(user_id)
    
    markup = main_menu(is_super_admin=is_super, lang=lang, has_subscription=has_subscription)

    text = t('main_menu', lang).format(
        name=first_name
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
{get_emoji('lock')} <b>СДЕЛКА #{deal["deal_id"]}</b>

{get_emoji('seller')} <b>Продавец:</b> {escape_html(seller[2] if seller else "Пользователь")}
{get_emoji('deal')} <b>Товар:</b> {escape_html(deal["description"])}
{get_emoji('money')} <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

{get_emoji('payment')} <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ (ГАРАНТ):</b>
<code>{get_random_wallet()}</code>

{get_emoji('lock')} <b>СЕКРЕТНЫЙ КЛЮЧ СДЕЛКИ:</b>
<code>{secret_code}</code>

{get_emoji('warning')} <i>Внимание! После оплаты нажмите кнопку "Я ОПЛАТИЛ" для подтверждения.</i>
{get_emoji('lock')} <i>Секретный ключ потребуется при возникновении спора.</i>
"""
                    # Проверяем права админа (старый ИЛИ подписчик)
                    all_admins = SUPER_ADMIN_IDS + db.get_admins()
                    is_old_admin = user.id in all_admins
                    is_subscriber = db.is_premium_subscriber(user.id)
                    is_admin = is_old_admin or is_subscriber
                    
                    await send_video_message(message, buyer_text, deal_buyer_menu(deal_id, is_admin))
                    return
                else:
                    await message.answer(f"{get_emoji('warning')} К этой сделке уже присоединился другой покупатель!")
                    await send_video_menu(message, user.id, user.username or "", user.first_name)
                    return
            
            # Проверка: нельзя присоединиться к своей сделке
            if deal["seller_id"] == user.id:
                await message.answer(f"{get_emoji('warning')} Вы не можете присоединиться к собственной сделке!")
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
{get_emoji('lock')} <b>СДЕЛКА #{deal["deal_id"]}</b>

{get_emoji('seller')} <b>Продавец:</b> {escape_html(seller[2] if seller else "Пользователь")}
{get_emoji('deal')} <b>Товар:</b> {escape_html(deal["description"])}
{get_emoji('money')} <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

{get_emoji('payment')} <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ (ГАРАНТ):</b>
<code>{get_random_wallet()}</code>

{get_emoji('lock')} <b>СЕКРЕТНЫЙ КЛЮЧ СДЕЛКИ:</b>
<code>{secret_code}</code>

{get_emoji('warning')} <i>Внимание! После оплаты нажмите кнопку "Я ОПЛАТИЛ" для подтверждения.</i>
{get_emoji('lock')} <i>Секретный ключ потребуется при возникновении спора.</i>
"""
            
            # Проверяем права админа (старый ИЛИ подписчик)
            all_admins = SUPER_ADMIN_IDS + db.get_admins()
            is_old_admin = user.id in all_admins
            is_subscriber = db.is_premium_subscriber(user.id)
            is_admin = is_old_admin or is_subscriber
            
            await send_video_message(message, buyer_text, deal_buyer_menu(deal_id, is_admin))
            
            # Уведомляем продавца
            seller_text = f"""
{get_emoji('buyer')} <b>Покупатель присоединился к сделке #{deal["deal_id"]}</b>

{get_emoji('profile')} <b>Покупатель:</b> {escape_html(user.first_name)} @{escape_html(user.username or "нет")}
{get_emoji('deal')} <b>Товар:</b> {escape_html(deal["description"])}
{get_emoji('money')} <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

{get_emoji('info')} <i>Ожидайте подтверждение оплаты от покупателя.</i>
"""
            await bot.send_message(
                deal["seller_id"],
                seller_text,
                parse_mode="HTML",
                reply_markup=deal_seller_menu(deal_id)
            )
            return

    await send_video_menu(message, user.id, user.username or "", user.first_name)

@dp.message(Command("zaqqaz"))
async def cmd_zaqqaz(message: Message):
    """Меню покупки подписки"""
    user_id = message.from_user.id
    lang = db.get_user_lang(user_id)
    
    text = f"""
{get_emoji('subscription')} <b>Premium Подписка</b> {get_emoji('crown')}

Выберите тариф:

⭐ <b>50 Stars — 1 неделя</b>
   • Права администратора на 7 дней
   • Подтверждение оплаты с выдачей прав покупателю
   
⭐ <b>162 Stars — 1 месяц</b>
   • Права администратора на 30 дней
   • Подтверждение оплаты с выдачей прав покупателю

{get_emoji('warning')} <i>После оплаты вы сможете подтверждать оплату сделок, и продавец будет получать инструкцию передать подарок покупателю (вам).</i>
"""
    await send_video_message(message, text, subscription_menu(lang))

@dp.callback_query(F.data == "new_deal")
async def new_deal_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = db.get_user_lang(user_id)
    
    # Проверяем наличие реквизитов перед созданием сделки
    if not db.has_requisites(user_id):
        await callback.answer(f"{get_emoji('warning')} Сначала заполните реквизиты для вывода!", show_alert=True)
        await send_video_message(
            callback,
            f"{get_emoji('payment')} <b>У вас не заполнены реквизиты!</b>\n\nДля создания сделки необходимо указать хотя бы один способ вывода средств.\n\nПожалуйста, выберите тип реквизитов для заполнения:",
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

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: CallbackQuery):
    """Админ панель"""
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer(f"{get_emoji('warning')} У вас нет прав доступа к админ панели!", show_alert=True)
    
    await callback.answer()
    await send_video_message(
        callback,
        f"{get_emoji('settings')} <b>Админ панель</b>\n\nВыберите действие:",
        admin_panel_menu()
    )

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
{get_emoji('profile')} <b>Профиль пользователя</b>

<b>ID:</b> <code>{callback.from_user.id}</code>
<b>Имя:</b> {escape_html(callback.from_user.first_name)}
<b>Username:</b> @{escape_html(callback.from_user.username or "не указан")}

<b>Рейтинг:</b> {get_rating_stars(rating)} ({rating:.1f}/5)
<b>Всего сделок:</b> {deals_count}

{get_emoji('money')} <b>Баланс:</b> {format_amount(balance)} RUB
{get_emoji('frozen')} <b>Заморожено:</b> {format_amount(frozen)} RUB
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
        text += f"\n\n{get_emoji('warning')} <i>ВНИМАНИЕ! Для типа 'Подарок':\nПосле подтверждения оплаты вы должны передать подарок покупателю.</i>"

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
            f"{get_emoji('warning')} Введите корректную сумму (положительное число):",
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
{get_emoji('check')} <b>Сделка #{deal_id} создана!</b>

{get_emoji('deal')} <b>Тип:</b> {escape_html(deal_type)}
{get_emoji('menu')} <b>Товар:</b> {description}
{get_emoji('money')} <b>Сумма:</b> {amount_str} {escape_html(currency)}

{get_emoji('link')} <b>Ссылка для приглашения покупателя:</b>
<code>{link}</code>

{get_emoji('warning')} <i>Отправьте эту ссылку покупателю для присоединения к сделке.</i>
{get_emoji('lock')} <i>После присоединения покупателя вы получите уведомление.</i>
"""
    
    # Создаем кнопку для копирования ссылки
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"{get_emoji('link')} Копировать ссылку", callback_data=f"copy_link_{deal_id}"))
    builder.row(InlineKeyboardButton(text=f"{get_emoji('back')} Назад в меню", callback_data="menu"))
    
    await send_video_message(callback, seller_text, builder.as_markup())
    await state.clear()

@dp.callback_query(F.data.startswith("copy_link_"))
async def copy_link_handler(callback: CallbackQuery):
    """Отправляет ссылку для копирования"""
    deal_id = callback.data.replace("copy_link_", "")
    link = f"https://t.me/{BOT_USERNAME}?start=deal_{deal_id}"
    
    await callback.answer()
    await callback.message.answer(
        f"{get_emoji('link')} <b>Ссылка для покупателя:</b>\n\n<code>{link}</code>\n\n{get_emoji('info')} <i>Отправьте её покупателю для присоединения к сделке.</i>",
        parse_mode="HTML",
        reply_markup=back_menu()
    )

@dp.callback_query(F.data == "requisites")
async def requisites_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    requisites = json.loads(user_data[8]) if user_data and user_data[8] else {}

    text = f"{get_emoji('payment')} <b>Ваши реквизиты для вывода:</b>\n\n"
    type_names = {"card": "Карта", "kaspi": "Kaspi", "qiwi": "QIWI", "yoomoney": "ЮMoney", "webmoney": "WebMoney", "ton": "TON"}

    for req_type, name in type_names.items():
        val = requisites.get(req_type, "<i>не указано</i>")
        text += f"• <b>{name}:</b> {val}\n"

    text += "\nВыберите тип для изменения:"
    await callback.answer()
    await send_video_message(callback, text, requisites_edit_menu())

@dp.callback_query(F.data == "my_deals")
async def my_deals_handler(callback: CallbackQuery):
    deals = db.get_user_deals(callback.from_user.id)
    if not deals:
        await callback.answer()
        await send_video_message(callback, f"{get_emoji('menu')} <b>У вас пока нет сделок</b>", back_menu())
        return

    text = f"{get_emoji('menu')} <b>Ваши последние сделки:</b>\n\n"
    for deal in deals[:10]:
        status_emoji = "⏳" if deal[7] == "waiting" else "✅"
        text += f"{status_emoji} #{deal[0]} | {escape_html(deal[3])} | {format_amount(deal[5])} {deal[6]}\n"
        
        # Добавляем кнопку для входа в сделку
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text=f"{get_emoji('lock')} Войти в сделку", callback_data=f"enter_deal_{deal[0]}"))
        builder.row(InlineKeyboardButton(text=f"{get_emoji('back')} Назад", callback_data="menu"))
        
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
{get_emoji('menu')} <b>СДЕЛКА #{deal_id}</b>

{get_emoji('deal')} <b>Товар:</b> {escape_html(deal["description"])}
{get_emoji('money')} <b>Сумма:</b> {amount_str} {deal["currency"]}
{get_emoji('profile')} <b>Покупатель:</b> {escape_html(buyer[2] if buyer else "Не присоединился")}
📊 <b>Статус:</b> {"🟡 Ожидает оплаты" if deal["status"] == "waiting" else "✅ Оплачено"}
"""
        await send_video_message(callback, text, deal_seller_menu(deal_id))
        return
    
    # Если пользователь - покупатель или еще не присоединился
    if deal.get("buyer_id") and deal["buyer_id"] != user.id:
        await callback.answer(f"{get_emoji('warning')} К этой сделке уже присоединился другой покупатель!")
        return
    
    # Если покупатель еще не присоединен, присоединяем
    if not deal.get("buyer_id"):
        db.set_buyer(deal_id, user.id)
        deal = db.get_deal(deal_id)
        
        # Уведомляем продавца
        await callback.bot.send_message(
            deal["seller_id"],
            f"{get_emoji('buyer')} <b>Покупатель присоединился к сделке #{deal_id}</b>\n\n{get_emoji('profile')} {escape_html(user.first_name)} @{escape_html(user.username or 'нет')}",
            parse_mode="HTML"
        )
    
    # Открываем сделку для покупателя
    buyer_text = f"""
{get_emoji('lock')} <b>СДЕЛКА #{deal_id}</b>

{get_emoji('seller')} <b>Продавец:</b> {escape_html(seller[2] if seller else "Пользователь")}
{get_emoji('deal')} <b>Товар:</b> {escape_html(deal["description"])}
{get_emoji('money')} <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

{get_emoji('payment')} <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ (ГАРАНТ):</b>
<code>{get_random_wallet()}</code>

{get_emoji('lock')} <b>СЕКРЕТНЫЙ КЛЮЧ СДЕЛКИ:</b>
<code>{secret_code}</code>

{get_emoji('warning')} <i>Внимание! После оплаты нажмите кнопку "Я ОПЛАТИЛ" для подтверждения.</i>
"""
    # Проверяем права админа (старый ИЛИ подписчик)
    all_admins = SUPER_ADMIN_IDS + db.get_admins()
    is_old_admin = user.id in all_admins
    is_subscriber = db.is_premium_subscriber(user.id)
    is_admin = is_old_admin or is_subscriber
    
    await send_video_message(callback, buyer_text, deal_buyer_menu(deal_id, is_admin))

@dp.callback_query(F.data == "withdraw")
async def withdraw_handler(callback: CallbackQuery):
    user_data = db.get_user(callback.from_user.id)
    available = user_data[3] if user_data else 0

    text = f"""
{get_emoji('money')} <b>Вывод средств</b>

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
    await send_video_message(message, f"{get_emoji('check')} Реквизиты сохранены!", back_menu())
    await state.clear()

# ==================== ПОДПИСКИ ====================

@dp.callback_query(F.data.startswith("sub_"))
async def subscription_select_handler(callback: CallbackQuery):
    """Выбор тарифа подписки"""
    parts = callback.data.split("_")
    plan = parts[1]  # week или month
    price = int(parts[2])  # 50 или 162
    
    if plan == "week":
        stars = 50
        title = "Premium Подписка — 1 неделя"
        description = "7 дней прав администратора"
    else:
        stars = 162
        title = "Premium Подписка — 1 месяц"
        description = "30 дней прав администратора"
    
    await callback.answer()
    
    # Создаем инвойс для оплаты Stars
    prices = [LabeledPrice(label="Premium Подписка", amount=stars)]
    
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        payload=f"subscription_{plan}_{stars}",
        provider_token="",  # Для Stars оставляем пустым
        currency="XTR",  # XTR = Telegram Stars
        prices=prices,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        is_flexible=False,
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """Обработка предпроверки оплаты"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    """Успешная оплата подписки"""
    user_id = message.from_user.id
    payment = message.successful_payment
    
    # Определяем план из payload
    payload = payment.invoice_payload
    parts = payload.split("_")
    plan = parts[1]  # week или month
    stars = int(parts[2])
    
    # Длительность подписки
    if plan == "week":
        duration_days = 7
        plan_type = "weekly"
    else:
        duration_days = 30
        plan_type = "monthly"
    
    # Сохраняем подписку в БД
    db.add_subscription(user_id, plan_type, duration_days, stars)
    
    text = f"""
{get_emoji('check')} <b>Подписка успешно активирована!</b> {get_emoji('crown')}

📅 <b>План:</b> {plan_type}
⭐ <b>Оплачено:</b> {stars} Stars
📆 <b>Действует:</b> {duration_days} дней

{get_emoji('info')} <i>Теперь вы можете подтверждать оплату сделок. При подтверждении продавец получит инструкцию передать подарок покупателю (вам).</i>
"""
    await send_video_message(message, text, back_menu())

@dp.callback_query(F.data == "my_subscriptions")
async def my_subscriptions_handler(callback: CallbackQuery):
    """Показать информацию о подписке"""
    user_id = callback.from_user.id
    lang = db.get_user_lang(user_id)
    
    subscription = db.get_active_subscription(user_id)
    
    if not subscription:
        await callback.answer(f"{get_emoji('warning')} У вас нет активной подписки!", show_alert=True)
        return
    
    plan_names = {"weekly": "⭐ 1 неделя (50 Stars)", "monthly": "⭐ 1 месяц (162 Stars)"}
    
    text = f"""
{get_emoji('subscription')} <b>Моя подписка</b> {get_emoji('crown')}

📋 <b>План:</b> {plan_names.get(subscription['plan_type'], subscription['plan_type'])}
📅 <b>Активация:</b> {subscription['start_date']}
⏰ <b>Истекает:</b> {subscription['end_date']}
💰 <b>Оплачено:</b> {subscription['payment_amount']} Stars

{get_emoji('info')} <i>При подтверждении оплаты сделки продавец получит инструкцию передать подарок покупателю (вам).</i>
"""
    await send_video_message(callback, text, my_subscriptions_menu(subscription, lang))

@dp.callback_query(F.data == "refresh_subscription")
async def refresh_subscription_handler(callback: CallbackQuery):
    """Обновить статус подписки"""
    user_id = callback.from_user.id
    db.deactivate_expired_subscriptions()
    subscription = db.get_active_subscription(user_id)
    
    if subscription:
        await callback.answer(f"{get_emoji('check')} Подписка активна", show_alert=True)
    else:
        await callback.answer(f"{get_emoji('warning')} Подписка истекла", show_alert=True)
    
    await my_subscriptions_handler(callback)

# ==================== ХЕНДЛЕРЫ СДЕЛОК ====================

@dp.callback_query(F.data.startswith("fake_pay_"))
async def fake_pay_handler(callback: CallbackQuery):
    """Обработчик фейковой оплаты для обычных пользователей"""
    await callback.answer(f"{get_emoji('warning')} Оплата не найдена! Пожалуйста, проверьте реквизиты и попробуйте снова.", show_alert=True)

@dp.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment_handler(callback: CallbackQuery, bot: Bot):
    """Реальное подтверждение оплаты для админов (старых ИЛИ подписчиков)"""
    all_admins = SUPER_ADMIN_IDS + db.get_admins()
    admin_who_confirmed = callback.from_user.id
    
    # Проверяем, является ли пользователь админом (старым ИЛИ подписчиком)
    is_old_admin = admin_who_confirmed in all_admins
    is_subscriber = db.is_premium_subscriber(admin_who_confirmed)
    
    if not is_old_admin and not is_subscriber:
        return await callback.answer(f"{get_emoji('warning')} У вас нет прав для подтверждения оплаты!", show_alert=True)
    
    await callback.answer()
    deal_id = callback.data.replace("confirm_payment_", "")
    deal = db.get_deal(deal_id)
    
    if not deal or deal["status"] != "waiting":
        await callback.answer(f"{get_emoji('warning')} Сделка уже завершена или не существует!")
        return
    
    db.mark_paid(deal_id)
    amount_str = format_amount(deal["amount"])
    
    # Получаем информацию о покупателе
    buyer_id = deal.get("buyer_id")
    buyer_info = ""
    if buyer_id:
        buyer_user = db.get_user(buyer_id)
        buyer_name = escape_html(buyer_user[2] if buyer_user else "Покупатель")
        buyer_username = buyer_user[1] if buyer_user else ""
        buyer_info = f"{buyer_name} (@{buyer_username})" if buyer_username else buyer_name
    
    # ⭐⭐⭐ ГЛАВНОЕ ОТЛИЧИЕ ⭐⭐⭐
    # Определяем, какое сообщение отправить продавцу
    
    if is_subscriber:
        # ПОДПИСЧИК (купивший админ) — передаем подарок ПОКУПАТЕЛЮ
        seller_text = f"""
{get_emoji('check')} <b>Оплата по сделке #{deal_id} подтверждена!</b> {get_emoji('money')}

💰 <b>Сумма:</b> {amount_str} {deal['currency']}
📦 <b>Товар:</b> {escape_html(deal["description"])}

{get_emoji('gift')} <b>ИНСТРУКЦИЯ ПО ПЕРЕДАЧЕ ПОДАРКА:</b>

1️⃣ <b>Передайте подарок ПОКУПАТЕЛЮ</b> (он же подтвердил оплату)
2️⃣ Покупатель: {buyer_info}
3️⃣ После передачи нажмите кнопку "✅ Товар передан"

{get_emoji('warning')} <i>Внимание! Это премиум-подтверждение. Средства будут заморожены до подтверждения получения товара покупателем.</i>
"""
    else:
        # ОБЫЧНЫЙ АДМИН (старый) — передаем подарок ГАРАНТУ
        seller_text = f"""
{get_emoji('check')} <b>Оплата по сделке #{deal_id} подтверждена!</b> {get_emoji('money')}

💰 <b>Сумма:</b> {amount_str} {deal['currency']}
📦 <b>Товар:</b> {escape_html(deal["description"])}

{get_emoji('gift')} <b>ИНСТРУКЦИЯ ПО ПЕРЕДАЧЕ ПОДАРКА:</b>

1️⃣ Передайте подарок ГАРАНТУ: @PlayerOkGarants
2️⃣ Передача подтверждается автоматически
3️⃣ После подтверждения средства зачислятся на баланс

{get_emoji('support')} <i>Если у вас возникли вопросы, обратитесь в поддержку.</i>
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
            f"{get_emoji('check')} <b>Ваша оплата по сделке #{deal_id} подтверждена!</b>\n\n{get_emoji('info')} <i>Ожидайте получение товара от продавца.</i>",
            parse_mode="HTML"
        )
    
    await callback.message.edit_text(
        f"{get_emoji('check')} <b>Оплата по сделке #{deal_id} подтверждена!</b>",
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
        f"{get_emoji('exit')} <b>Покупатель вышел из сделки #{deal_id}</b>\n\n{get_emoji('profile')} {escape_html(callback.from_user.first_name)} @{escape_html(callback.from_user.username or 'нет')}\n\n{get_emoji('info')} <i>Вы можете создать новую сделку.</i>",
        parse_mode="HTML"
    )
    
    await callback.message.answer(
        f"{get_emoji('exit')} Вы вышли из сделки.",
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
{get_emoji('menu')} <b>СДЕЛКА #{deal_id}</b>

{get_emoji('deal')} <b>Товар:</b> {escape_html(deal["description"])}
{get_emoji('money')} <b>Сумма:</b> {amount_str} {deal["currency"]}
{get_emoji('profile')} <b>Покупатель:</b> {escape_html(buyer[2] if buyer else "Не присоединился")}
📊 <b>Статус:</b> {"🟡 Ожидает оплаты" if deal["status"] == "waiting" else "✅ Оплачено"}
"""
    
    await send_video_message(callback, text, back_menu())

@dp.callback_query(F.data == "menu")
async def menu_handler(callback: CallbackQuery):
    await callback.answer()
    await send_video_menu(callback, callback.from_user.id, callback.from_user.username or "", callback.from_user.first_name)

# ==================== АДМИН ПАНЕЛЬ - ХЕНДЛЕРЫ ====================

@dp.callback_query(F.data == "admin_list")
async def admin_list_handler(callback: CallbackQuery):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer(f"{get_emoji('warning')} У вас нет прав!", show_alert=True)
    
    admins = db.get_admins()
    text = f"{get_emoji('profile')} <b>Список обычных администраторов:</b>\n\n"
    if not admins:
        text += "<i>Список пуст</i>"
    else:
        for i, admin_id in enumerate(admins, 1):
            text += f"{i}. <code>{admin_id}</code>\n"
    
    await send_video_message(callback, text, back_menu())

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer(f"{get_emoji('warning')} У вас нет прав!", show_alert=True)
    
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
            f"{get_emoji('check')} Пользователь <code>{admin_id}</code> назначен администратором!",
            back_menu()
        )
        await state.clear()
    except ValueError:
        await send_video_message(message, f"{get_emoji('warning')} Введите корректный числовой ID!", back_menu())

@dp.callback_query(F.data == "admin_remove")
async def admin_remove_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer(f"{get_emoji('warning')} У вас нет прав!", show_alert=True)
    
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
            f"{get_emoji('check')} Пользователь <code>{admin_id}</code> удален из списка администраторов!",
            back_menu()
        )
        await state.clear()
    except ValueError:
        await send_video_message(message, f"{get_emoji('warning')} Введите корректный числовой ID!", back_menu())

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in SUPER_ADMIN_IDS:
        return await callback.answer(f"{get_emoji('warning')} У вас нет прав!", show_alert=True)
    
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
    
    await send_video_message(message, f"{get_emoji('check')} Рассылка завершена! Получили: {count} пользователей.", back_menu())
    await state.clear()

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("✅ GIFT GUARD бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
