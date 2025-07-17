from aiogram import Bot, Dispatcher
from handlers import router
from scheduler import SchedulerManager
import logging
import asyncio

logging.basicConfig(level=logging.INFO)

API_TOKEN = 'YOUR TOKEN'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

async def main():
    dp.include_router(router)
    logging.info("Router registered successfully.")
    scheduler_manager = SchedulerManager(bot)
    scheduler_manager.start()
    logging.info("Scheduler initialized.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())