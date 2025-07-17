from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import TaskManager
from aiogram import Bot
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SchedulerManager:
    def __init__(self, bot: Bot):
        self.scheduler = AsyncIOScheduler()
        self.bot = bot
        self.task_manager = TaskManager()

    async def check_deadlines(self):
        try:
            users = set(task.user_id for task in self.task_manager.get_all_incomplete_tasks())
            for user_id in users:
                tasks = [task for task in self.task_manager.get_tasks(user_id, completed=0) if task.deadline]
                for task in tasks:
                    deadline_time = datetime.strptime(task.deadline, '%d.%m.%Y %H:%M')
                    if deadline_time <= datetime.now() + timedelta(minutes=15) and deadline_time > datetime.now():
                        await self.bot.send_message(user_id, f'⏰ Уведомление: Задача "{task.text}" в категории "{task.category}" истекает через 15 минут! Дедлайн: {task.deadline}')
                        logger.info(f"Sent deadline reminder for task {task.id} to user {user_id}")
        except Exception as e:
            logger.error(f"Error in check_deadlines: {e}")

    def start(self):
        self.scheduler.add_job(self.check_deadlines, 'interval', minutes=1, misfire_grace_time=30)
        self.scheduler.start()
        logger.info("Scheduler started.")