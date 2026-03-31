# main.py
# PlayerOk | Гарант-Бот — P2P Escrow для Telegram
# python-telegram-bot v20.x | SQLite | Railway-ready

import os
import random
import string
import logging
from datetime import datetime
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Video, constants
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, Filters
)
from telegram.error import BadRequest

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНСТАНТЫ ====================
BOT_TOKEN = os.getenv('BOT_TOKEN', '8799843968:AAHmwgNjBYQJJZAI4MVlpohE4wHat3X_6zQ')
MAIN_ADMIN_ID = int(os.getenv('MAIN_ADMIN_ID', '8717189451'))

# Курсы валют
USDT_TO_RUB = 90
TON_TO_USDT = 6.5
PX_TO_USDT = 42
FEE_PERCENT = 1.01  # +1% комиссия

# Состояния для ConversationHandler
(
    WAITING_RUB_AMOUNT,
    WAITING_DESCRIPTION,
    WAITING_WALLET_TYPE,
    WAITING_WALLET_VALUE,
    WAITING_DELETE_WALLET,
) = range(5)

# Глобальные хранилища (для простоты в одном файле)
user_states = {}  # {user_id: {'state': ..., 'data': {...}}}

# ==================== БАЗА ДАННЫХ ====================import sqlite3

def init_db():
    """Инициализация базы данных SQLite"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referrer_id INTEGER,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица реквизитов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            wallet_type TEXT NOT NULL,
            wallet_value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(user_id, wallet_type)
        )
    ''')
    
    # Таблица админов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (added_by) REFERENCES admins(user_id)
        )
    ''')
    
    # Таблица сделок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id TEXT PRIMARY KEY,
            seller_id INTEGER NOT NULL,
            buyer_id INTEGER,
            amount_rub REAL NOT NULL,            amount_usdt REAL,
            amount_ton REAL,
            amount_px REAL,
            description TEXT,
            payment_address TEXT,
            payment_memo TEXT,
            status TEXT DEFAULT 'created',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users(user_id),
            FOREIGN KEY (buyer_id) REFERENCES users(user_id)
        )
    ''')
    
    # Индексы для ускорения поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deals_seller ON deals(seller_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_wallets_user ON user_wallets(user_id)')
    
    # Добавляем главного админа
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)', 
                   (MAIN_ADMIN_ID, MAIN_ADMIN_ID))
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def get_db():
    """Получение соединения с БД"""
    conn = sqlite3.connect('bot.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def generate_deal_id(length: int = 11) -> str:
    """Генерация уникального ID сделки (буквы + цифры)"""
    chars = string.ascii_uppercase + string.digits
    while True:
        deal_id = ''.join(random.choices(chars, k=length))
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM deals WHERE id = ?', (deal_id,))
        if not cursor.fetchone():
            conn.close()
            return deal_id
        conn.close()

def convert_currency(amount_rub: float) -> dict:
    """Конвертация суммы RUB в USDT, TON, PX"""    usdt = round(amount_rub / USDT_TO_RUB, 2)
    ton = round(usdt / TON_TO_USDT, 4)
    px = round(usdt * PX_TO_USDT * FEE_PERCENT, 2)  # с комиссией 1%
    return {
        'usdt': usdt,
        'ton': ton,
        'px': px
    }

def generate_payment_address(deal_id: str) -> str:
    """Генерация адреса для оплаты (заглушка для демо)"""
    # В продакшене здесь будет интеграция с TON/крипто-провайдером
    return f"EQA{deal_id[:4]}_DEMO_ADDRESS_{deal_id[-4:]}"

async def send_video_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          text: str, keyboard: InlineKeyboardMarkup, 
                          message_id: Optional[int] = None):
    """Отправка меню с видео-анимацией, удаление старого сообщения"""
    try:
        # Удаляем предыдущее сообщение если есть ID
        if message_id and update.effective_chat:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=message_id
            )
    except BadRequest:
        pass  # Сообщение уже удалено или не найдено
    
    # Отправляем новое сообщение с видео
    try:
        with open('welcome.mp4', 'rb') as video_file:
            message = await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video_file,
                caption=text,
                reply_markup=keyboard,
                parse_mode=constants.ParseMode.HTML
            )
            return message.message_id
    except FileNotFoundError:
        logger.warning("Файл welcome.mp4 не найден, отправляем текст")
        message = await update.effective_message.reply_text(
            text, 
            reply_markup=keyboard,
            parse_mode=constants.ParseMode.HTML
        )
        return message.message_id

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None or user_id == MAIN_ADMIN_ID

def get_user_wallets(user_id: int) -> list:
    """Получение реквизитов пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT wallet_type, wallet_value FROM user_wallets WHERE user_id = ?', (user_id,))
    wallets = cursor.fetchall()
    conn.close()
    return [dict(row) for row in wallets]

def has_wallets(user_id: int) -> bool:
    """Проверка наличия хотя бы одного реквизита"""
    return len(get_user_wallets(user_id)) > 0

async def save_user(update: Update, referrer_id: Optional[int] = None):
    """Сохранение/обновление данных пользователя"""
    user = update.effective_user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, username, first_name, last_name, referrer_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name
    ''', (user.id, user.username, user.first_name, user.last_name, referrer_id))
    conn.commit()
    conn.close()

# ==================== КЛАВИАТУРЫ ====================

def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [InlineKeyboardButton("💰 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton("👛 Мои реквизиты", callback_data="my_wallets")],
        [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="ref_link")],
        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_lang")],
        [InlineKeyboardButton("🆘 Поддержка", callback_data="support")],
    ]
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)
def wallets_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню управления реквизитами"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 TON Кошелёк", callback_data="wallet_ton")],
        [InlineKeyboardButton("📱 СБП (телефон)", callback_data="wallet_sbp")],
        [InlineKeyboardButton("🏦 Карта РФ", callback_data="wallet_rf")],
        [InlineKeyboardButton("🇺🇦 Карта UA", callback_data="wallet_ua")],
        [InlineKeyboardButton("⭐ STARS", callback_data="wallet_stars")],
        [InlineKeyboardButton("🗑 Удалить реквизит", callback_data="delete_wallet")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ])

def deal_created_keyboard(deal_id: str) -> InlineKeyboardMarkup:
    """Кнопки после создания сделки"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Скопировать ссылку", 
                             url=f"https://t.me/PlrkNFTBot?start=deal_{deal_id}")],
        [InlineKeyboardButton("❌ Отменить сделку", callback_data=f"cancel_deal_{deal_id}")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back_to_main")],
    ])

def buyer_deal_keyboard(deal_id: str) -> InlineKeyboardMarkup:
    """Кнопки для покупателя в сделке"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚪 Выйти из сделки", callback_data=f"exit_deal_{deal_id}")],
        [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_main")],
    ])

def admin_deal_keyboard(deal_id: str) -> InlineKeyboardMarkup:
    """Кнопки для админа при просмотре сделки"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_payment_{deal_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ])

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Админ-панель"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")],
        [InlineKeyboardButton("➖ Удалить админа", callback_data="admin_remove")],
        [InlineKeyboardButton("📋 Все сделки", callback_data="admin_deals")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")],
    ])

def confirm_delete_keyboard(wallet_type: str) -> InlineKeyboardMarkup:
    """Подтверждение удаления реквизита"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Да, удалить {wallet_type}", callback_data=f"confirm_del_{wallet_type}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="my_wallets")],    ])

# ==================== ОБРАБОТЧИКИ КОМАНД ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    args = context.args
    
    # Сохраняем пользователя
    referrer_id = None
    if args and args[0].startswith('ref_'):
        try:
            referrer_id = int(args[0].replace('ref_', ''))
            if referrer_id == user.id:
                referrer_id = None
        except ValueError:
            pass
    
    await save_user(update, referrer_id)
    
    # Проверка на переход по сделке
    if args and args[0].startswith('deal_'):
        deal_id = args[0].replace('deal_', '')
        await join_deal(update, context, deal_id)
        return
    
    # Главное меню
    text = (
        "🏦 PlayerOk | Гарант-Бот\n\n"
        "Добро пожаловать в надёжный P2P-гарант!\n\n"
        "Выберите нужный раздел:"
    )
    await send_video_menu(update, context, text, main_menu_keyboard(user.id))

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    user = update.effective_user
    # Очищаем состояние пользователя
    user_states.pop(user.id, None)
    
    text = (
        "🏦 PlayerOk | Гарант-Бот\n\n"
        "Добро пожаловать в надёжный P2P-гарант!\n\n"
        "Выберите нужный раздел:"
    )
    await send_video_menu(update, context, text, main_menu_keyboard(user.id))

# ==================== УПРАВЛЕНИЕ РЕКВИЗИТАМИ ====================
async def my_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр реквизитов пользователя"""
    user = update.effective_user
    wallets = get_user_wallets(user.id)
    
    if not wallets:
        text = "👛 Ваши реквизиты\n\nУ вас пока нет добавленных реквизитов.\nДобавьте хотя бы один для создания сделок:"
    else:
        text = "👛 Ваши реквизиты\n\n"
        type_names = {
            'ton': '💎 TON', 'sbp': '📱 СБП', 'rf': '🏦 Карта РФ',
            'ua': '🇺🇦 Карта UA', 'stars': '⭐ STARS'
        }
        for w in wallets:
            text += f"{type_names.get(w['wallet_type'], w['wallet_type'])}: `{w['wallet_value']}`\n"
        text += "\n✏️ Выберите действие:"
    
    await send_video_menu(update, context, text, wallets_menu_keyboard(), 
                         update.effective_message.message_id if update.effective_message else None)

async def add_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_type: str):
    """Начало добавления реквизита"""
    user = update.effective_user
    user_states[user.id] = {'state': WAITING_WALLET_TYPE, 'data': {'type': wallet_type}}
    
    type_names = {
        'ton': '💎 TON Кошелёк', 'sbp': '📱 СБП (телефон)', 
        'rf': '🏦 Карта РФ', 'ua': '🇺🇦 Карта UA', 'stars': '⭐ STARS'
    }
    
    text = f"➕ Добавление {type_names.get(wallet_type, wallet_type)}\n\nВведите значение реквизита:"
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="my_wallets")]])
    await send_video_menu(update, context, text, keyboard, 
                         update.effective_message.message_id if update.effective_message else None)
    return WAITING_WALLET_VALUE

async def save_wallet_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение значения реквизита"""
    user = update.effective_user
    state = user_states.get(user.id, {})
    
    if state.get('state') != WAITING_WALLET_VALUE:
        await update.effective_message.reply_text("⚠️ Ошибка: неверная последовательность действий")
        return ConversationHandler.END
    
    wallet_type = state['data'].get('type')
    wallet_value = update.effective_message.text.strip()
    
    if not wallet_value:        await update.effective_message.reply_text("❌ Значение не может быть пустым")
        return WAITING_WALLET_VALUE
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO user_wallets (user_id, wallet_type, wallet_value)
            VALUES (?, ?, ?)
        ''', (user.id, wallet_type, wallet_value))
        conn.commit()
        text = f"✅ Реквизит {wallet_type} успешно добавлен!"
    except Exception as e:
        logger.error(f"Ошибка сохранения реквизита: {e}")
        text = "❌ Ошибка при сохранении реквизита"
    finally:
        conn.close()
    
    user_states.pop(user.id, None)
    await send_video_menu(update, context, text, wallets_menu_keyboard(),
                         update.effective_message.message_id if update.effective_message else None)
    return ConversationHandler.END

async def delete_wallet_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления реквизита"""
    user = update.effective_user
    wallets = get_user_wallets(user.id)
    
    if not wallets:
        text = "🗑 Удаление реквизита\n\nУ вас нет реквизитов для удаления."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="my_wallets")]])
        await send_video_menu(update, context, text, keyboard,
                             update.effective_message.message_id if update.effective_message else None)
        return ConversationHandler.END
    
    text = "🗑 Удаление реквизита\n\nВыберите реквизит для удаления:"
    buttons = []
    for w in wallets:
        type_names = {'ton': '💎', 'sbp': '📱', 'rf': '🏦', 'ua': '🇺🇦', 'stars': '⭐'}
        name = type_names.get(w['wallet_type'], '•')
        buttons.append([InlineKeyboardButton(f"{name} {w['wallet_type']}: {w['wallet_value'][:20]}...", 
                                            callback_data=f"del_wallet_{w['wallet_type']}")])
    buttons.append([InlineKeyboardButton("🔙 Отмена", callback_data="my_wallets")])
    
    await send_video_menu(update, context, text, InlineKeyboardMarkup(buttons),
                         update.effective_message.message_id if update.effective_message else None)
    user_states[user.id] = {'state': WAITING_DELETE_WALLET}
    return WAITING_DELETE_WALLET

async def confirm_delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_type: str):    """Подтверждение удаления реквизита"""
    user = update.effective_user
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_wallets WHERE user_id = ? AND wallet_type = ?', (user.id, wallet_type))
    conn.commit()
    conn.close()
    
    text = f"✅ Реквизит {wallet_type} успешно удалён!"
    user_states.pop(user.id, None)
    await send_video_menu(update, context, text, wallets_menu_keyboard(),
                         update.effective_message.message_id if update.effective_message else None)
    return ConversationHandler.END

# ==================== СОЗДАНИЕ СДЕЛКИ ====================

async def create_deal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания сделки"""
    user = update.effective_user
    
    # Проверка наличия реквизитов
    if not has_wallets(user.id):
        text = "⚠️ Сначала добавьте реквизиты!\n\nБез реквизитов нельзя создать сделку.\nПерейдите в раздел «Мои реквизиты»:"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👛 Мои реквизиты", callback_data="my_wallets")],
                                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
        await send_video_menu(update, context, text, keyboard,
                             update.effective_message.message_id if update.effective_message else None)
        return ConversationHandler.END
    
    text = "💰 Создание сделки\n\nВведите сумму в RUB (например: 5000):"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]])
    await send_video_menu(update, context, text, keyboard,
                         update.effective_message.message_id if update.effective_message else None)
    
    user_states[user.id] = {'state': WAITING_RUB_AMOUNT, 'data': {}}
    return WAITING_RUB_AMOUNT

async def get_rub_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение суммы в RUB"""
    user = update.effective_user
    try:
        amount = float(update.effective_message.text.strip().replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.effective_message.reply_text("❌ Введите корректную сумму (число больше 0)")
        return WAITING_RUB_AMOUNT
    
    user_states[user.id]['data']['amount_rub'] = amount
        text = "📝 Описание товара\n\nУкажите, что вы предлагаете в этой сделке:"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]])
    await send_video_menu(update, context, text, keyboard,
                         update.effective_message.message_id if update.effective_message else None)
    return WAITING_DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания и создание сделки"""
    user = update.effective_user
    description = update.effective_message.text.strip()
    
    if len(description) < 5:
        await update.effective_message.reply_text("❌ Описание слишком короткое (минимум 5 символов)")
        return WAITING_DESCRIPTION
    
    # Генерация данных сделки
    deal_id = generate_deal_id()
    amounts = convert_currency(user_states[user.id]['data']['amount_rub'])
    payment_address = generate_payment_address(deal_id)
    
    # Сохранение в БД
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO deals (id, seller_id, amount_rub, amount_usdt, amount_ton, amount_px, 
                          description, payment_address, payment_memo, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'created')
    ''', (deal_id, user.id, user_states[user.id]['data']['amount_rub'], 
          amounts['usdt'], amounts['ton'], amounts['px'], description, 
          payment_address, deal_id))
    conn.commit()
    conn.close()
    
    # Ссылка для покупателя
    link = f"https://t.me/PlrkNFTBot?start=deal_{deal_id}"
    
    # Сообщение об успехе
    text = (
        f"✅ Сделка успешно создана!\n\n"
        f"💰 Сумма: {user_states[user.id]['data']['amount_rub']} RUB\n"
        f"📝 Описание: {description}\n\n"
        f"🔗 Ссылка для покупателя:\n{link}"
    )
    
    user_states.pop(user.id, None)
    await send_video_menu(update, context, text, deal_created_keyboard(deal_id),
                         update.effective_message.message_id if update.effective_message else None)
    return ConversationHandler.END

# ==================== ПРИСОЕДИНЕНИЕ К СДЕЛКЕ ====================
async def join_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Присоединение покупателя к сделке"""
    user = update.effective_user
    conn = get_db()
    cursor = conn.cursor()
    
    # Поиск сделки
    cursor.execute('SELECT * FROM deals WHERE id = ?', (deal_id,))
    deal = cursor.fetchone()
    
    if not deal:
        text = "❌ Сделка не найдена!\nВозможно, ссылка устарела или неверна."
        await send_video_menu(update, context, text, main_menu_keyboard(user.id))
        conn.close()
        return
    
    deal = dict(deal)
    
    # Проверка: не покупает ли продавец свой товар
    if deal['seller_id'] == user.id:
        text = "❌ Нельзя купить свой товар!\nВы являетесь продавцом в этой сделке."
        await send_video_menu(update, context, text, main_menu_keyboard(user.id))
        conn.close()
        return
    
    # Проверка статуса сделки
    if deal['status'] != 'created':
        text = f"⚠️ Статус сделки: {deal['status']}\nДействия по этой сделке временно недоступны."
        await send_video_menu(update, context, text, main_menu_keyboard(user.id))
        conn.close()
        return
    
    # Получение данных продавца
    cursor.execute('SELECT username FROM users WHERE user_id = ?', (deal['seller_id'],))
    seller = cursor.fetchone()
    seller_username = seller['username'] if seller and seller['username'] else f"user_{deal['seller_id']}"
    
    # Обновление сделки: добавляем покупателя
    cursor.execute('UPDATE deals SET buyer_id = ?, status = ? WHERE id = ?', 
                   (user.id, 'waiting_payment', deal_id))
    conn.commit()
    conn.close()
    
    # Сохранение покупателя в БД
    await save_user(update)
    
    # Сообщение покупателю
    text = (
        f"📌 Информация о сделке #{deal_id}\n\n"        f"👤 Вы покупатель в сделке.\n"
        f"👨‍💼 Продавец: @{seller_username}\n"
        f"🛍 Вы покупаете: {deal['description']}\n\n"
        f"💳 Адрес для оплаты:\n`{deal['payment_address']}`\n\n"
        f"💰 Сумма к оплате:\n"
        f"• {deal['amount_px']} PX (+1% fee)\n"
        f"• {deal['amount_usdt']} USDT\n"
        f"• {deal['amount_ton']} TON\n\n"
        f"📝 Комментарий к платежу (мемо):\n`{deal['payment_memo']}`"
    )
    
    await send_video_menu(update, context, text, buyer_deal_keyboard(deal_id),
                         update.effective_message.message_id if update.effective_message else None)
    
    # Уведомление продавцу
    buyer_username = user.username or f"user_{user.id}"
    seller_text = f"👤 Пользователь @{buyer_username} присоединился к сделке\n📌 #{deal_id}\n⚠️ Проверьте, что это тот же пользователь!"
    
    try:
        await context.bot.send_message(chat_id=deal['seller_id'], text=seller_text)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление продавцу: {e}")

async def exit_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Выход покупателя из сделки"""
    user = update.effective_user
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM deals WHERE id = ?', (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or deal['buyer_id'] != user.id:
        text = "❌ Вы не являетесь участником этой сделки."
        await send_video_menu(update, context, text, main_menu_keyboard(user.id))
        conn.close()
        return
    
    # Отмена сделки
    cursor.execute('UPDATE deals SET buyer_id = NULL, status = ? WHERE id = ?', ('cancelled', deal_id))
    conn.commit()
    conn.close()
    
    text = f"✅ Вы успешно вышли из сделки #{deal_id}"
    await send_video_menu(update, context, text, main_menu_keyboard(user.id),
                         update.effective_message.message_id if update.effective_message else None)

async def cancel_deal(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Отмена сделки продавцом"""
    user = update.effective_user    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM deals WHERE id = ?', (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or deal['seller_id'] != user.id:
        text = "❌ Вы не являетесь продавцом в этой сделке."
        await send_video_menu(update, context, text, main_menu_keyboard(user.id))
        conn.close()
        return
    
    if deal['status'] != 'created':
        text = "❌ Нельзя отменить сделку в текущем статусе."
        await send_video_menu(update, context, text, main_menu_keyboard(user.id))
        conn.close()
        return
    
    # Уведомление покупателю если есть
    if deal['buyer_id']:
        try:
            await context.bot.send_message(
                chat_id=deal['buyer_id'],
                text=f"⚠️ Продавец отменил сделку #{deal_id}"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить покупателя: {e}")
    
    # Удаление сделки
    cursor.execute('DELETE FROM deals WHERE id = ?', (deal_id,))
    conn.commit()
    conn.close()
    
    text = f"✅ Сделка #{deal_id} успешно отменена"
    await send_video_menu(update, context, text, main_menu_keyboard(user.id),
                         update.effective_message.message_id if update.effective_message else None)

# ==================== ПОДТВЕРЖДЕНИЕ ОПЛАТЫ (АДМИНЫ) ====================

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str):
    """Подтверждение оплаты админом"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.effective_message.reply_text("❌ Доступ запрещён")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM deals WHERE id = ?', (deal_id,))    deal = cursor.fetchone()
    
    if not deal:
        text = "❌ Сделка не найдена"
        await send_video_menu(update, context, text, main_menu_keyboard(user.id))
        conn.close()
        return
    
    deal = dict(deal)
    
    # Обновление статуса
    cursor.execute('UPDATE deals SET status = ? WHERE id = ?', ('paid', deal_id))
    conn.commit()
    conn.close()
    
    # Уведомление продавцу
    seller_text = (
        f"✅ Оплата подтверждена!\n\n"
        f"Сделка #{deal_id}\n"
        f"Сумма: {deal['amount_rub']} RUB\n\n"
        f"Можете передать товар."
    )
    try:
        await context.bot.send_message(chat_id=deal['seller_id'], text=seller_text)
    except Exception as e:
        logger.error(f"Не удалось уведомить продавца: {e}")
    
    # Уведомление покупателю
    if deal['buyer_id']:
        buyer_text = (
            f"✅ Оплата подтверждена!\n\n"
            f"Сделка #{deal_id}\n"
            f"Ожидайте товар от продавца."
        )
        try:
            await context.bot.send_message(chat_id=deal['buyer_id'], text=buyer_text)
        except Exception as e:
            logger.error(f"Не удалось уведомить покупателя: {e}")
    
    text = f"✅ Оплата по сделке #{deal_id} подтверждена!"
    await send_video_menu(update, context, text, main_menu_keyboard(user.id),
                         update.effective_message.message_id if update.effective_message else None)

# ==================== АДМИН-ПАНЕЛЬ ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображение админ-панели"""
    user = update.effective_user
    
    if not is_admin(user.id):        await update.effective_message.reply_text("❌ Доступ запрещён")
        return
    
    text = "⚙️ Админ-панель\n\nВыберите действие:"
    await send_video_menu(update, context, text, admin_panel_keyboard(),
                         update.effective_message.message_id if update.effective_message else None)

async def admin_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление админа"""
    user = update.effective_user
    
    if user.id != MAIN_ADMIN_ID:
        await update.effective_message.reply_text("❌ Только главный админ может добавлять админов")
        return
    
    text = "➕ Добавить админа\n\nВведите @username нового админа (без @):"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")]])
    await send_video_menu(update, context, text, keyboard,
                         update.effective_message.message_id if update.effective_message else None)
    
    user_states[user.id] = {'state': 'admin_add_username'}
    return 'admin_add_username'

async def admin_add_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка username для добавления админа"""
    user = update.effective_user
    
    if user_states.get(user.id, {}).get('state') != 'admin_add_username':
        return ConversationHandler.END
    
    username = update.effective_message.text.strip().lstrip('@')
    
    # Поиск пользователя по username (в реальном боте нужен get_chat)
    try:
        chat = await context.bot.get_chat(f"@{username}")
        new_admin_id = chat.id
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)', 
                      (new_admin_id, user.id))
        conn.commit()
        conn.close()
        
        text = f"✅ Пользователь @{username} добавлен в админы!"
        # Уведомление новому админу
        try:
            await context.bot.send_message(
                chat_id=new_admin_id,
                text=f"🎉 Вы добавлены в админы бота @PlrkNFTBot"            )
        except:
            pass
    except Exception as e:
        logger.error(f"Ошибка добавления админа: {e}")
        text = f"❌ Не удалось найти пользователя @{username}"
    
    user_states.pop(user.id, None)
    await send_video_menu(update, context, text, admin_panel_keyboard(),
                         update.effective_message.message_id if update.effective_message else None)
    return ConversationHandler.END

async def admin_remove_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление админа"""
    user = update.effective_user
    
    if user.id != MAIN_ADMIN_ID:
        await update.effective_message.reply_text("❌ Только главный админ может удалять админов")
        return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT u.username FROM admins a JOIN users u ON a.user_id = u.user_id WHERE a.user_id != ?', (MAIN_ADMIN_ID,))
    admins = cursor.fetchall()
    conn.close()
    
    if not admins:
        text = "➖ Удаление админа\n\nНет админов для удаления."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        await send_video_menu(update, context, text, keyboard,
                             update.effective_message.message_id if update.effective_message else None)
        return
    
    text = "➖ Удаление админа\n\nВыберите админа для удаления:"
    buttons = [[InlineKeyboardButton(f"@{a['username']}", callback_data=f"admin_del_{a['username']}")] for a in admins]
    buttons.append([InlineKeyboardButton("🔙 Отмена", callback_data="admin_panel")])
    
    await send_video_menu(update, context, text, InlineKeyboardMarkup(buttons),
                         update.effective_message.message_id if update.effective_message else None)

async def admin_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str):
    """Подтверждение удаления админа"""
    user = update.effective_user
    
    if user.id != MAIN_ADMIN_ID:
        await update.effective_message.reply_text("❌ Доступ запрещён")
        return
    
    conn = get_db()
    cursor = conn.cursor()    cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    
    if result:
        cursor.execute('DELETE FROM admins WHERE user_id = ?', (result['user_id'],))
        conn.commit()
        text = f"✅ Админ @{username} удалён!"
    else:
        text = f"❌ Пользователь @{username} не найден"
    
    conn.close()
    await send_video_menu(update, context, text, admin_panel_keyboard(),
                         update.effective_message.message_id if update.effective_message else None)

# ==================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ====================

async def ref_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация реферальной ссылки"""
    user = update.effective_user
    ref_link = f"https://t.me/PlrkNFTBot?start=ref_{user.id}"
    
    text = f"🔗 Ваша реферальная ссылка:\n\n`{ref_link}`\n\nПриглашайте друзей и получайте бонусы!"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
    await send_video_menu(update, context, text, keyboard,
                         update.effective_message.message_id if update.effective_message else None)

async def change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Смена языка (заглушка)"""
    text = "🌐 Смена языка\n\nФункция в разработке. Скоро будет доступно несколько языков!"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
    await send_video_menu(update, context, text, keyboard,
                         update.effective_message.message_id if update.effective_message else None)

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контакты поддержки"""
    text = "🆘 Поддержка\n\nСвязаться с поддержкой: @PlayerOkSupport\n\nМы ответим в ближайшее время!"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])
    await send_video_menu(update, context, text, keyboard,
                         update.effective_message.message_id if update.effective_message else None)

# ==================== ОБРАБОТЧИК CALLBACK_QUERIES ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
        # Навигация
    if data == "back_to_main":
        await back_to_main(update, context)
    
    # Главное меню
    elif data == "create_deal":
        return await create_deal_start(update, context)
    elif data == "my_wallets":
        await my_wallets(update, context)
    elif data == "ref_link":
        await ref_link(update, context)
    elif data == "change_lang":
        await change_lang(update, context)
    elif data == "support":
        await support(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    
    # Реквизиты
    elif data.startswith("wallet_"):
        wallet_type = data.replace("wallet_", "")
        return await add_wallet_start(update, context, wallet_type)
    elif data == "delete_wallet":
        return await delete_wallet_start(update, context)
    elif data.startswith("del_wallet_"):
        wallet_type = data.replace("del_wallet_", "")
        return await confirm_delete_wallet(update, context, wallet_type)
    
    # Сделки
    elif data.startswith("cancel_deal_"):
        deal_id = data.replace("cancel_deal_", "")
        await cancel_deal(update, context, deal_id)
    elif data.startswith("exit_deal_"):
        deal_id = data.replace("exit_deal_", "")
        await exit_deal(update, context, deal_id)
    elif data.startswith("confirm_payment_"):
        deal_id = data.replace("confirm_payment_", "")
        await confirm_payment(update, context, deal_id)
    
    # Админ-панель
    elif data == "admin_add":
        return await admin_add_start(update, context)
    elif data == "admin_remove":
        await admin_remove_start(update, context)
    elif data.startswith("admin_del_"):
        username = data.replace("admin_del_", "")
        await admin_remove_confirm(update, context, username)
    elif data == "admin_deals":
        text = "📋 Все сделки (функция в разработке)"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])        await send_video_menu(update, context, text, keyboard, query.message.message_id)

# ==================== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ====================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений для состояний"""
    user = update.effective_user
    state = user_states.get(user.id, {}).get('state')
    
    if state == WAITING_RUB_AMOUNT:
        return await get_rub_amount(update, context)
    elif state == WAITING_DESCRIPTION:
        return await get_description(update, context)
    elif state == WAITING_WALLET_VALUE:
        return await save_wallet_value(update, context)
    elif state == 'admin_add_username':
        return await admin_add_username(update, context)
    
    # Если нет активного состояния - игнорируем
    return ConversationHandler.END

# ==================== ЗАПУСК БОТА ====================

def main():
    """Точка входа"""
    # Инициализация БД
    init_db()
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для диалогов
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lambda u, c: create_deal_start(u, c), pattern="^create_deal$"),
            CallbackQueryHandler(lambda u, c: my_wallets(u, c), pattern="^my_wallets$"),
            CallbackQueryHandler(lambda u, c: add_wallet_start(u, c, 'ton'), pattern="^wallet_ton$"),
            CallbackQueryHandler(lambda u, c: add_wallet_start(u, c, 'sbp'), pattern="^wallet_sbp$"),
            CallbackQueryHandler(lambda u, c: add_wallet_start(u, c, 'rf'), pattern="^wallet_rf$"),
            CallbackQueryHandler(lambda u, c: add_wallet_start(u, c, 'ua'), pattern="^wallet_ua$"),
            CallbackQueryHandler(lambda u, c: add_wallet_start(u, c, 'stars'), pattern="^wallet_stars$"),
            CallbackQueryHandler(lambda u, c: delete_wallet_start(u, c), pattern="^delete_wallet$"),
            CallbackQueryHandler(lambda u, c: admin_add_start(u, c), pattern="^admin_add$"),
        ],
        states={
            WAITING_RUB_AMOUNT: [MessageHandler(Filters.TEXT & ~Filters.COMMAND, get_rub_amount)],
            WAITING_DESCRIPTION: [MessageHandler(Filters.TEXT & ~Filters.COMMAND, get_description)],
            WAITING_WALLET_VALUE: [MessageHandler(Filters.TEXT & ~Filters.COMMAND, save_wallet_value)],
            WAITING_DELETE_WALLET: [CallbackQueryHandler(
                lambda u, c: confirm_delete_wallet(u, c, u.callback_query.data.replace('del_wallet_', '')),                pattern="^del_wallet_")],
            'admin_add_username': [MessageHandler(Filters.TEXT & ~Filters.COMMAND, admin_add_username)],
        },
        fallbacks=[CallbackQueryHandler(button_handler)],
        allow_reentry=True
    )
    
    # Регистрация хендлеров
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, text_handler))
    
    # Запуск
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()3
