import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8781583236:AAH5Q8jsctHKvELugiR_O85ppFsLdVeo75I")
BOT_USERNAME = os.getenv("BOT_USERNAME", "PlayerOkRunbot")
SUPER_ADMIN_IDS = [int(x) for x in os.getenv("SUPER_ADMIN_IDS", "8717189451,8072028362").split(",")]

# ID берем ИЗ ТОКЕНА
BOT_ID = int(BOT_TOKEN.split(":")[0])  # Будет 8799843968

PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "")  # Для Stars пока не нужен
