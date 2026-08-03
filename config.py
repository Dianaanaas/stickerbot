import os
from dotenv import load_dotenv

load_dotenv() 
# Токен вашего бота, полученный от @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID чата/группы, куда будут пересылаться обращения от клиентов.
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID")) 

# Название вашего магазина (используется в текстах бота)
SHOP_NAME = os.getenv("SHOP_NAME", "Click&Stick")

# Ссылка на сайт
SHOP_URL = os.getenv("SHOP_URL", "https://clickandstick.tilda.ws/")
