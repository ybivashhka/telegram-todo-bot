from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import calendar

class Calendar:
    @staticmethod
    def create_calendar(year=None, month=None):
        now = datetime.now()
        year = year or now.year
        month = month or now.month
        if year < now.year or (year == now.year and month < now.month):
            year, month = now.year, now.month
        month_name = calendar.month_name[month]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"{month_name} {year}", callback_data="ignore"),
            InlineKeyboardButton(text="⬅", callback_data=f"prev_month_{year}_{month}"),
            InlineKeyboardButton(text="➡", callback_data=f"next_month_{year}_{month}")
        ])
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=day, callback_data="ignore") for day in days])
        cal = calendar.monthcalendar(year, month)
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
                else:
                    is_disabled = (year == now.year and month == now.month and day < now.day)
                    callback_data = f"day_{year}_{month}_{day}" if not is_disabled else "ignore"
                    row.append(InlineKeyboardButton(text=str(day), callback_data=callback_data))
            keyboard.inline_keyboard.append(row)
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Пропустить", callback_data="skip_deadline")])
        return keyboard

    @staticmethod
    def create_time_picker():
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute // 30 * 30
        times = [f"{h:02d}:{m:02d}" for h in range(0, 24) for m in (0, 30)]
        for i in range(0, len(times), 4):
            row = []
            for time in times[i:i+4]:
                hour, minute = map(int, time.split(':'))
                is_disabled = (hour < current_hour or (hour == current_hour and minute < current_minute))
                callback_data = f"time_{time}" if not is_disabled else "ignore"
                row.append(InlineKeyboardButton(text=time, callback_data=callback_data))
            keyboard.inline_keyboard.append(row)
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Пропустить", callback_data="skip_deadline")])
        return keyboard

calendar_instance = Calendar()

def create_calendar(year=None, month=None):
    return calendar_instance.create_calendar(year, month)

def create_time_picker():
    return calendar_instance.create_time_picker()