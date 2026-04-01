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
    deal_confirm_menu,
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
                await message.answer("❌ К этой сделке уже присоединился покупатель!")
                await send_video_menu(message, user.id, user.username or "", user.first_name)
                return
            
            # Присоединяем покупателя
            db.set_buyer(deal_id, user.id)
            deal = db.get_deal(deal_id)
            amount_str = format_amount(deal["amount"])
            seller = db.get_user(deal["seller_id"])
            
            # Получаем секретный код из базы (с проверкой)
            secret_code = deal.get("secret_code")
            if not secret_code:
                secret_code = f"{random.randint(100000, 999999)}"
            
            # Получаем реквизиты продавца
            seller_requisites = json.loads(seller[8]) if seller and seller[8] else {}
            ton_wallet = seller_requisites.get("ton", "Не указан")
            
            # Проверяем, есть ли у продавца реквизиты
            if not seller_requisites or ton_wallet == "Не указан":
                await message.answer("⚠️ У продавца не заполнены реквизиты TON кошелька! Свяжитесь с поддержкой.")
                await send_video_menu(message, user.id, user.username or "", user.first_name)
                return
            
            # Текст для покупателя
            buyer_text = f"""
🔐 <b>СДЕЛКА #{deal["deal_id"]}</b>

👤 <b>Продавец:</b> {escape_html(seller[2] if seller else "Пользователь")}
📦 <b>Товар:</b> {escape_html(deal["description"])}
💰 <b>Сумма:</b> {amount_str} {escape_html(deal["currency"])}

<b>💳 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:</b>
<code>{ton_wallet}</code>

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
    lang = db.get_user_lang(callback.from_user.id)
    await callback.answer()
    await send_video_message(
        callback,
        t('select_type', lang),
        deal_type_menu(lang=lang)
    )
    await state.set_state(DealStates.waiting_deal_type)

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

    text = t('deal_created', lang).format(
        type=escape_html(deal_type),
        desc=description,
        amount=amount_str,
        cur=escape_html(currency),
        id=deal_id,
        link=link
    )
    await send_video_message(callback, text, back_menu())
    await state.clear()

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

    await callback.answer()
    await send_video_message(callback, text, back_menu())

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
    
    # Уведомляем продавца
    await bot.send_message(
        deal["seller_id"],
        f"✅ <b>Оплата по сделке #{deal_id} подтверждена!</b>\n\n💰 Сумма: {amount_str} {deal['currency']}\n\n<i>Теперь вы можете передать товар покупателю.</i>",
        parse_mode="HTML"
    )
    
    # Уведомляем покупателя, если есть
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
