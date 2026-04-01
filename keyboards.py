from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu(is_super_admin: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    from utils import t

    builder.row(
        InlineKeyboardButton(text=t('new_deal', lang), callback_data="new_deal"),
        InlineKeyboardButton(text=t('my_deals', lang), callback_data="my_deals")
    )
    builder.row(
        InlineKeyboardButton(text=t('profile', lang), callback_data="profile"),
        InlineKeyboardButton(text=t('requisites', lang), callback_data="requisites")
    )
    builder.row(
        InlineKeyboardButton(text=t('withdraw', lang), callback_data="withdraw"),
        InlineKeyboardButton(text=t('scam_base', lang), callback_data="scam_base")
    )
    # Кнопка для ВСЕХ пользователей
    builder.row(
        InlineKeyboardButton(text="🔄 Восстановить сделку", callback_data="restore_deal")
    )

    if is_super_admin:
        builder.row(
            InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add"),
            InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_remove")
        )
        builder.row(
            InlineKeyboardButton(text="📝 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="👥 Список админов", callback_data="admin_list")
        )

    builder.row(
        InlineKeyboardButton(text=t('channel', lang), url="https://t.me/playerok"),
        InlineKeyboardButton(text=t('support', lang), url="https://t.me/playerok")
    )

    builder.row(
        InlineKeyboardButton(text=t('language', lang), callback_data="lang_menu")
    )

    return builder.as_markup()


def lang_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    from utils import t
    builder.row(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton(text="🇺🇸 English", callback_data="set_lang_en")
    )
    builder.row(
        InlineKeyboardButton(text=t('back', lang), callback_data="menu")
    )
    return builder.as_markup()


def deal_type_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    from utils import t
    builder.row(
        InlineKeyboardButton(text=t('gift', lang), callback_data="type_gift"),
        InlineKeyboardButton(text=t('account', lang), callback_data="type_account")
    )
    builder.row(
        InlineKeyboardButton(text=t('other', lang), callback_data="type_other")
    )
    builder.row(
        InlineKeyboardButton(text=t('back', lang), callback_data="menu")
    )
    return builder.as_markup()


def currency_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇷🇺 RUB", callback_data="cur_RUB"),
        InlineKeyboardButton(text="🇰🇿 KZT", callback_data="cur_KZT"),
        InlineKeyboardButton(text="🇺🇦 UAH", callback_data="cur_UAH")
    )
    builder.row(
        InlineKeyboardButton(text="🇧🇾 BYN", callback_data="cur_BYN"),
        InlineKeyboardButton(text="🇪🇺 EUR", callback_data="cur_EUR"),
        InlineKeyboardButton(text="🇺🇸 USD", callback_data="cur_USD")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Stars", callback_data="cur_STARS"),
        InlineKeyboardButton(text="💎 TON", callback_data="cur_TON")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_deal_type")
    )
    return builder.as_markup()


def requisites_edit_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Карта", callback_data="req_card"),
        InlineKeyboardButton(text="🇰🇿 Kaspi", callback_data="req_kaspi")
    )
    builder.row(
        InlineKeyboardButton(text="💸 QIWI", callback_data="req_qiwi"),
        InlineKeyboardButton(text="💰 ЮMoney", callback_data="req_yoomoney")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 WebMoney", callback_data="req_webmoney"),
        InlineKeyboardButton(text="💎 TON", callback_data="req_ton")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()


def scam_base_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить пользователя", callback_data="check_user")
    )
    builder.row(
        InlineKeyboardButton(text="🚨 Сообщить о скамере", callback_data="report_scam")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu"))
    return builder.as_markup()


def deal_buyer_menu(deal_id: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для покупателя в сделке"""
    builder = InlineKeyboardBuilder()
    
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ ОПЛАТУ", callback_data=f"confirm_payment_{deal_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✅ Я ОПЛАТИЛ", callback_data=f"fake_pay_{deal_id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🚪 Выйти из сделки", callback_data=f"exit_deal_{deal_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()


def deal_seller_menu(deal_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для продавца после присоединения покупателя"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁️ Просмотр сделки", callback_data=f"view_deal_{deal_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
    )
    return builder.as_markup()
