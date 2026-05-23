import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.engine import init_db
from handlers import user, admin

logging.basicConfig(level=logging.INFO)

async def main():
    # Baza jadvallarini yaratish/ulash
    await init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Botni ishga tushirish (Long Polling)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
