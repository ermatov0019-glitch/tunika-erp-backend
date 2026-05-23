import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database.engine import init_db
from handlers import user, admin

logging.basicConfig(level=logging.INFO)

async def health_check(request):
    return web.Response(text="Tunika ERP Bot is running successfully!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Dummy web server started on port {port}")

async def main():
    # Baza jadvallarini yaratish/ulash
    await init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Routerlarni ulash
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Render xatosini oldini olish uchun yordamchi server ishga tushirish
    await start_dummy_server()

    # Botni ishga tushirish (Long Polling)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
