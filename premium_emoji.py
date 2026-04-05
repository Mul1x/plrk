# premium_emoji.py
# Сюда ты будешь вставлять ID премиум-эмодзи из бота @FIND_MY_ID_BOT
# Если premium_id = None — используется обычный emoji

PREMIUM_EMOJI_CONFIG = {
    "star": {"default": "⭐", "premium_id": 5449449325434266744},
    "crown": {"default": "👑", "premium_id": 5267500801240092311},
    "check": {"default": "✅", "premium_id": 5217822164362739968},
    "time": {"default": "⏰", "premium_id": 5206607081334906820},
    "menu": {"default": "📋", "premium_id": 5382194935057372936},
    "subscription": {"default": "💎", "premium_id": 5197269100878907942},
    "warning": {"default": "⚠️", "premium_id": 5427168083074628963},
    "lock": {"default": "🔐", "premium_id": 5447644880824181073},
    "gift": {"default": "🎁", "premium_id": 5296369303661067030},
    "profile": {"default": "👤", "premium_id": 5278702045883292456},
    "money": {"default": "💰", "premium_id": 5406683434124859552},
    "settings": {"default": "⚙️", "premium_id": 5409048419211682843},
    "link": {"default": "🔗", "premium_id": 5341715473882955310},
    "info": {"default": "ℹ️", "premium_id": 5447410659077661506},
    "deal": {"default": "📦", "premium_id": 5334544901428229844},
    "buyer": {"default": "👥", "premium_id": 5406683434124859552},
    "seller": {"default": "👤", "premium_id": 5411225014148014586},
    "payment": {"default": "💳", "premium_id": 5411225014148014586},
    "withdraw": {"default": "🏧", "premium_id": 5445353829304387411},
    "support": {"default": "🆘", "premium_id": 5445353829304387411},
    "language": {"default": "🌐", "premium_id": 5443038326535759644},
    "back": {"default": "◀️", "premium_id": 5447410659077661506},
    "exit": {"default": "🚪", "premium_id": 5447183459602669338},
    "video": {"default": "🎬", "premium_id": 5416041192905265756},
    "rating": {"default": "⭐", "premium_id": 5282843764451195532},
    "frozen": {"default": "❄️", "premium_id": 5438496463044752972},
}


def get_emoji(key: str) -> str:
    """Возвращает HTML-тег с премиум-эмодзи, если есть ID, иначе обычный emoji"""
    data = PREMIUM_EMOJI_CONFIG.get(key, {})
    premium_id = data.get("premium_id")
    default = data.get("default", "•")
    
    if premium_id and str(premium_id).strip():
        return f'<tg-emoji emoji-id="{premium_id}">{default}</tg-emoji>'
    return default


def replace_emojis_in_text(text: str) -> str:
    """Заменяет все плейсхолдеры {emoji:key} на премиум-эмодзи или обычные"""
    import re
    pattern = r'\{emoji:([a-z_]+)\}'
    
    def replacer(match):
        key = match.group(1)
        return get_emoji(key)
    
    return re.sub(pattern, replacer, text)
