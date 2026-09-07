import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "vadymtm90")
# DATABASE_URL теперь будет подставлена из переменной окружения Railway
DATABASE_URL = os.getenv("DATABASE_URL", "")

