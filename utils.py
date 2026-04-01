import html

def format_amount(amount: float) -> str:
    return f"{amount:,.2f}".replace(",", " ")

def get_rating_stars(rating: float) -> str:
    return "★" * int(rating) + "☆" * (5 - int(rating))

def escape_html(text: str) -> str:
    """Экранирует HTML-спецсимволы для безопасного отображения"""
    return html.escape(str(text))

MESSAGES = {
    'ru': {
        'main_menu': (
            "🎁 <b>PlayerOk</b> — Мы специализированный сервис по обеспечению безопасности вне биржевых сделок.\n\n"
            "<i>Автоматизированный алгоритм исполнения.\n"
            "Скорость и автоматизация.\n"
            "Удобный и быстрый вывод средств.</i>\n\n"
            "• Комиссия сервиса: <b>3%</b>\n"
            "• Режим работы: <b>24/7</b>\n\n"
            "💰 <b>Выплачено всего:</b> <code>{total} RUB</code>\n\n"
            "⭐ <b>Рейтинг:</b> {rating} <code>{val}/5</code>  •  🤝 <b>Сделок:</b> <code>{deals}</code>\n\n"
            "<i>Выберите нужный раздел ниже:</i>"
        ),
        'new_deal': "🟢 Новая сделка",
        'my_deals': "📋 Мои сделки",
        'profile': "👤 Профиль",
        'requisites': "💳 Реквизиты",
        'withdraw': "💰 Вывод",
        'scam_base': "⚠️ Скам‑база",
        'channel': "📢 Канал",
        'support': "🆘 Поддержка",
        'language': "🌐 Язык",
        'select_type': "📦 <b>Выберите тип сделки:</b>",
        'gift': "🎁 Подарок",
        'account': "👤 Аккаунт",
        'other': "📦 Другое",
        'back': "◀️ Назад в меню",
        'select_currency': "💱 <b>Выберите валюту</b>\n\nСумма: <code>{amount}</code>",
        'deal_created': (
            "✅ <b>Сделка успешно создана!</b>\n\n"
            "📦 <b>Тип:</b> {type}\n"
            "📋 <b>Товар:</b> {desc}\n"
            "💵 <b>Сумма:</b> <code>{amount} {cur}</code>\n"
            "🔑 <b>ID сделки:</b> <code>#{id}</code>\n\n"
            "🔗 <b>Ссылка для покупателя:</b>\n"
            "<code>{link}</code>\n\n"
            "⚠️ <i>Передавайте товар только после получения уведомления об оплате!</i>"
        ),
        'lang_btn': "🇷🇺 Русский",
        'pay_btn': "✅ Оплатить",
        'cancel_btn': "❌ Отмена",
        'select_lang': "🌐 <b>Выберите язык интерфейса:</b>",
        'buyer_paid': (
            "💰 <b>Покупатель оплатил сделку</b> <code>#{id}</code>\n\n"
            "📦 <b>Тип:</b> {type}\n"
            "📋 <b>Товар:</b> {desc}\n"
            "💵 <b>Сумма:</b> <code>+{amount} {cur}</code>\n"
            "👤 <b>Покупатель:</b> <code>ID {buyer_id}</code>\n\n"
            "<i>✅ Деньги поступили — можете передавать товар или подарок.</i>\n\n"
            "🎁 <b>Инструкция по передаче подарка:</b>\n\n"
            "1️⃣ Передайте подарок гаранту: @PlayerokGarants\n"
            "2️⃣ Передача подтверждается автоматически\n"
            "3️⃣ После подтверждения средства зачислятся на баланс"
        ),
    },
    'en': {
        'main_menu': (
            "🎁 <b>PlayerOk</b> — We are a specialized service for ensuring security of off-exchange deals.\n\n"
            "<i>Automated execution algorithm.\n"
            "Speed and automation.\n"
            "Convenient and fast withdrawals.</i>\n\n"
            "• Service commission: <b>3%</b>\n"
            "• Working hours: <b>24/7</b>\n\n"
            "💰 <b>Total paid out:</b> <code>{total} RUB</code>\n\n"
            "⭐ <b>Rating:</b> {rating} <code>{val}/5</code>  •  🤝 <b>Deals:</b> <code>{deals}</code>\n\n"
            "<i>Select the section below:</i>"
        ),
        'new_deal': "🟢 New Deal",
        'my_deals': "📋 My Deals",
        'profile': "👤 Profile",
        'requisites': "💳 Requisites",
        'withdraw': "💰 Withdraw",
        'scam_base': "⚠️ Scam Base",
        'channel': "📢 Channel",
        'support': "🆘 Support",
        'language': "🌐 Language",
        'select_type': "📦 <b>Select deal type:</b>",
        'gift': "🎁 Gift",
        'account': "👤 Account",
        'other': "📦 Other",
        'back': "◀️ Back to menu",
        'select_currency': "💱 <b>Select currency</b>\n\nAmount: <code>{amount}</code>",
        'deal_created': (
            "✅ <b>Deal created successfully!</b>\n\n"
            "📦 <b>Type:</b> {type}\n"
            "📋 <b>Item:</b> {desc}\n"
            "💵 <b>Amount:</b> <code>{amount} {cur}</code>\n"
            "🔑 <b>Deal ID:</b> <code>#{id}</code>\n\n"
            "🔗 <b>Link for buyer:</b>\n"
            "<code>{link}</code>\n\n"
            "⚠️ <i>Transfer the item only after receiving payment notification!</i>"
        ),
        'lang_btn': "🇺🇸 English",
        'pay_btn': "✅ Pay",
        'cancel_btn': "❌ Cancel",
        'select_lang': "🌐 <b>Select interface language:</b>",
        'buyer_paid': (
            "💰 <b>Buyer paid for deal</b> <code>#{id}</code>\n\n"
            "📦 <b>Type:</b> {type}\n"
            "📋 <b>Item:</b> {desc}\n"
            "💵 <b>Amount:</b> <code>+{amount} {cur}</code>\n"
            "👤 <b>Buyer:</b> <code>ID {buyer_id}</code>\n\n"
            "<i>✅ Money received — you can transfer the item or gift.</i>\n\n"
            "🎁 <b>Gift transfer instructions:</b>\n\n"
            "1️⃣ Transfer the gift to the guarantor: @PlayerokGarants\n"
            "2️⃣ Transfer is confirmed automatically\n"
            "3️⃣ After confirmation, funds will be credited to your balance"
        ),
    }
}

def t(key: str, lang: str = 'ru') -> str:
    return MESSAGES.get(lang, MESSAGES['ru']).get(key, key)
