# premium_emoji.py
# Сюда ты будешь вставлять ID премиум-эмодзи из бота @FIND_MY_ID_BOT
# Если premium_id = None — используется обычный emoji

PREMIUM_EMOJI_CONFIG = {
    "star": {"default": "⭐", "premium_id": None},
    "crown": {"default": "👑", "premium_id": None},
    "check": {"default": "✅", "premium_id": None},
    "time": {"default": "⏰", "premium_id": None},
    "menu": {"default": "📋", "premium_id": None},
    "subscription": {"default": "💎", "premium_id": None},
    "warning": {"default": "⚠️", "premium_id": None},
    "lock": {"default": "🔐", "premium_id": None},
    "gift": {"default": "🎁", "premium_id": None},
    "profile": {"default": "👤", "premium_id": None},
    "money": {"default": "💰", "premium_id": None},
    "settings": {"default": "⚙️", "premium_id": None},
    "link": {"default": "🔗", "premium_id": None},
    "info": {"default": "ℹ️", "premium_id": None},
    "deal": {"default": "📦", "premium_id": None},
    "buyer": {"default": "👥", "premium_id": None},
    "seller": {"default": "👤", "premium_id": None},
    "payment": {"default": "💳", "premium_id": None},
    "withdraw": {"default": "🏧", "premium_id": None},
    "support": {"default": "🆘", "premium_id": None},
    "language": {"default": "🌐", "premium_id": None},
    "back": {"default": "◀️", "premium_id": None},
    "exit": {"default": "🚪", "premium_id": None},
    "video": {"default": "🎬", "premium_id": None},
    "rating": {"default": "⭐", "premium_id": None},
    "frozen": {"default": "❄️", "premium_id": None},
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
