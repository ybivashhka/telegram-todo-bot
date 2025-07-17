from aiogram import Router, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import Optional
from database import TaskManager
from states import AddTask, EditTask, SubtaskStates
from task_calendar import create_calendar, create_time_picker
from visualizer import generate_stats_plot
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = Router()
TASKS_PER_PAGE = 5
task_manager = TaskManager()

class KeyboardBuilder:
    @staticmethod
    def create_persistent_keyboard():
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="Главное меню")]
        ], resize_keyboard=True, one_time_keyboard=False)

    @staticmethod
    def create_main_menu():
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Добавить задачу", callback_data="cmd_add"),
                InlineKeyboardButton(text="Список задач", callback_data="cmd_list")
            ],
            [
                InlineKeyboardButton(text="Завершить задачу", callback_data="cmd_done"),
                InlineKeyboardButton(text="Редактировать", callback_data="cmd_edit")
            ],
            [
                InlineKeyboardButton(text="Статистика", callback_data="cmd_stats"),
                InlineKeyboardButton(text="Экспорт", callback_data="cmd_export")
            ]
        ])

    @staticmethod
    def create_category_keyboard(user_id, for_add=True):
        categories = task_manager.get_categories(user_id) or ['Общее']
        if 'Общее' not in categories:
            task_manager.add_category(user_id, 'Общее')
        keyboard = [[InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")] for cat in categories]
        if for_add:
            keyboard.append([InlineKeyboardButton(text="Новая категория", callback_data="new_category")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def create_task_keyboard(tasks, page, action, category=None):
        start_idx = page * TASKS_PER_PAGE
        end_idx = start_idx + TASKS_PER_PAGE
        paginated_tasks = tasks[start_idx:end_idx]
        keyboard = [[InlineKeyboardButton(text=f"{task.text} ({task.category})", callback_data=f"{action}_{task.id}")] for task in paginated_tasks]
        nav_row = []
        if start_idx > 0:
            nav_row.append(InlineKeyboardButton(text="⬅ Назад", callback_data=f"page_{action}_{page-1}_{category or ''}"))
        if end_idx < len(tasks):
            nav_row.append(InlineKeyboardButton(text="Далее ➡", callback_data=f"page_{action}_{page+1}_{category or ''}"))
        if nav_row:
            keyboard.append(nav_row)
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def create_subtask_keyboard(subtasks, task_id):
        keyboard = []
        for id, text, completed in subtasks:
            keyboard.append([InlineKeyboardButton(text=f"{text} {'(выполнено)' if completed else ''}", callback_data=f"sub_complete_{id}_{task_id}")])
        keyboard.append([InlineKeyboardButton(text="Добавить подзадачу", callback_data=f"add_sub_{task_id}")])
        if subtasks:
            delete_keyboard = []
            for id, text, _ in subtasks:
                delete_keyboard.append(InlineKeyboardButton(text=f"Удалить {text}", callback_data=f"sub_delete_{id}_{task_id}"))
                if len(delete_keyboard) == 2:
                    keyboard.append(delete_keyboard)
                    delete_keyboard = []
            if delete_keyboard:
                keyboard.append(delete_keyboard)
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def create_edit_field_keyboard(task_id):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Название", callback_data=f"edit_field_text_{task_id}")],
            [InlineKeyboardButton(text="Категория", callback_data=f"edit_field_category_{task_id}")],
            [InlineKeyboardButton(text="Дедлайн", callback_data=f"edit_field_deadline_{task_id}")]
        ])

@router.message(CommandStart())
async def start_command(message: types.Message):
    # Single message with persistent keyboard, no "Меню готово."
    await message.reply("Привет! Нажми 'Главное меню' ниже для действий.", reply_markup=KeyboardBuilder.create_persistent_keyboard())

@router.message(lambda m: m.text == "Главное меню")
async def show_main_menu(message: types.Message):
    await message.reply("Выбери действие:", reply_markup=KeyboardBuilder.create_main_menu())

@router.callback_query(lambda c: c.data.startswith("list_cat_") or c.data == "list_all_0")
async def list_by_category(callback: types.CallbackQuery):
    data = callback.data
    parts = data.split("_")
    category = parts[2] if len(parts) > 2 and parts[0] == "list" and parts[1] == "cat" else None
    page = int(parts[-1])
    tasks = task_manager.get_tasks(callback.from_user.id, completed=0, category=category)
    if not tasks:
        await callback.message.edit_text("Нет задач в этой категории.")
        await callback.answer()
        return
    keyboard = KeyboardBuilder.create_task_keyboard(tasks, page, "view", category)
    await callback.message.edit_text("Твои задачи:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == "cmd_list")
async def cmd_list(callback: types.CallbackQuery):
    # Handler for "Список задач" inline button
    categories = task_manager.get_categories(callback.from_user.id)
    keyboard = [[InlineKeyboardButton(text="Все задачи", callback_data="list_all_0")]]
    for cat in categories:
        keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"list_cat_{cat}_0")])
    await callback.message.edit_text("Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@router.callback_query(lambda c: c.data == "cmd_add")
async def add_task_command(callback: types.CallbackQuery, state: FSMContext):
    keyboard = KeyboardBuilder.create_category_keyboard(callback.from_user.id)
    await callback.message.edit_text("Выбери категорию:", reply_markup=keyboard)
    await state.set_state(AddTask.waiting_for_category)
    await callback.answer()

@router.callback_query(AddTask.waiting_for_category, lambda c: c.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "")
    await state.update_data(category=category)
    await callback.message.edit_text("Введи название задачи:")
    await state.set_state(AddTask.waiting_for_task)
    await callback.answer()

@router.callback_query(AddTask.waiting_for_category, lambda c: c.data == "new_category")
async def new_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи название новой категории:")
    await state.set_state(AddTask.waiting_for_new_category)
    await callback.answer()

@router.message(AddTask.waiting_for_new_category)
async def process_new_category(message: types.Message, state: FSMContext):
    category = message.text.strip()
    if not category or len(category) > 50:
        await message.reply("Категория не может быть пустой или слишком длинной.")
        return
    task_manager.add_category(message.from_user.id, category)
    await state.update_data(category=category)
    await message.reply("Категория добавлена. Введи название задачи:")
    await state.set_state(AddTask.waiting_for_task)

@router.message(AddTask.waiting_for_task)
async def process_task_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) > 200:
        await message.reply("Название не может быть пустым или слишком длинным.")
        return
    await state.update_data(text=text)
    keyboard = create_calendar()
    await message.reply("Выбери дату дедлайна:", reply_markup=keyboard)
    await state.set_state(AddTask.waiting_for_deadline_date)

@router.callback_query(AddTask.waiting_for_deadline_date, lambda c: c.data.startswith("day_") or c.data.startswith("prev_month_") or c.data.startswith("next_month_"))
async def process_date(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data.startswith("prev_month_") or data.startswith("next_month_"):
        parts = data.split("_")
        year = int(parts[2])
        month = int(parts[3])
        if data.startswith("prev_month_"):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        else:
            month += 1
            if month == 13:
                month = 1
                year += 1
        keyboard = create_calendar(year, month)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
        return
    if data == "skip_deadline":
        await save_task(callback, state, None)
        return
    parts = data.split("_")
    year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
    await state.update_data(date_str=f"{day:02d}.{month:02d}.{year}")
    keyboard = create_time_picker()
    await callback.message.edit_text("Выбери время дедлайна:", reply_markup=keyboard)
    await state.set_state(AddTask.waiting_for_deadline_time)

@router.callback_query(AddTask.waiting_for_deadline_time, lambda c: c.data.startswith("time_") or c.data == "skip_deadline")
async def process_time(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "skip_deadline":
        await save_task(callback, state, None)
        return
    time_str = data.split("_")[1]
    data = await state.get_data()
    date_str = data.get("date_str")
    deadline = f"{date_str} {time_str}" if date_str else None
    await save_task(callback, state, deadline)

async def save_task(callback: types.CallbackQuery, state: FSMContext, deadline: Optional[str]):
    data = await state.get_data()
    user_id = callback.from_user.id
    text = data.get("text")
    category = data.get("category")
    if task_manager.add_task(user_id, text, category, deadline):
        await callback.message.edit_text(f"Задача '{text}' добавлена в '{category}' с дедлайном {deadline or 'без'}.")
    else:
        await callback.message.edit_text("Ошибка добавления.")
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("view_"))
async def view_task_callback(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    task = next((t for t in task_manager.get_tasks(callback.from_user.id) if t.id == task_id), None)
    if task:
        subtasks = task_manager.get_subtasks(task_id)
        keyboard = KeyboardBuilder.create_subtask_keyboard(subtasks, task_id)
        text = f"Задача: {task.text}\nКатегория: {task.category}\nДедлайн: {task.deadline or 'Нет'}\nПодзадачи:"
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text("Задача не найдена.")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("add_sub_"))
async def add_subtask(callback: types.CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await callback.message.edit_text("Введи текст подзадачи:")
    await state.set_state(SubtaskStates.waiting_for_subtask)
    await callback.answer()

@router.message(StateFilter(SubtaskStates.waiting_for_subtask))
async def process_subtask_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) > 200:
        await message.reply("Текст не может быть пустым или слишком длинным.")
        return
    data = await state.get_data()
    task_id = data.get("task_id")
    if task_manager.add_subtask(task_id, text):
        await message.reply("Подзадача добавлена.")
    else:
        await message.reply("Ошибка добавления.")
    await state.clear()

@router.callback_query(lambda c: c.data.startswith("sub_complete_"))
async def complete_subtask(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    sub_id = int(parts[2])
    task_id = int(parts[3])
    task_manager.complete_subtask(sub_id)
    subtasks = task_manager.get_subtasks(task_id)
    keyboard = KeyboardBuilder.create_subtask_keyboard(subtasks, task_id)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("Подзадача обновлена.")

@router.callback_query(lambda c: c.data.startswith("sub_delete_"))
async def delete_subtask(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    sub_id = int(parts[2])
    task_id = int(parts[3])
    if task_manager.delete_subtask(sub_id):
        subtasks = task_manager.get_subtasks(task_id)
        keyboard = KeyboardBuilder.create_subtask_keyboard(subtasks, task_id)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer("Подзадача удалена.")
    else:
        await callback.answer("Ошибка удаления.")

@router.callback_query(lambda c: c.data == "cmd_done")
async def done_task_command(callback: types.CallbackQuery):
    tasks = task_manager.get_tasks(callback.from_user.id, completed=0)
    if not tasks:
        await callback.message.edit_text("Нет активных задач.")
        await callback.answer()
        return
    keyboard = KeyboardBuilder.create_task_keyboard(tasks, 0, "done")
    await callback.message.edit_text("Выбери задачу для завершения:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("done_"))
async def process_done_callback(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    if task_manager.complete_task(task_id):
        await callback.message.edit_text("Задача завершена!")
    else:
        await callback.message.edit_text("Ошибка.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "cmd_edit")
async def edit_task_command(callback: types.CallbackQuery, state: FSMContext):
    tasks = task_manager.get_tasks(callback.from_user.id, completed=0)
    if not tasks:
        await callback.message.edit_text("Нет активных задач.")
        await callback.answer()
        return
    keyboard = KeyboardBuilder.create_task_keyboard(tasks, 0, "edit_select")
    await callback.message.edit_text("Выбери задачу для редактирования:", reply_markup=keyboard)
    await state.set_state(EditTask.waiting_for_task)
    await callback.answer()

@router.callback_query(EditTask.waiting_for_task, lambda c: c.data.startswith("edit_select_"))
async def select_edit_task(callback: types.CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[2])
    await state.update_data(task_id=task_id)
    keyboard = KeyboardBuilder.create_edit_field_keyboard(task_id)
    await callback.message.edit_text("Что редактировать?", reply_markup=keyboard)
    await state.set_state(EditTask.waiting_for_field)
    await callback.answer()

@router.callback_query(EditTask.waiting_for_field, lambda c: c.data.startswith("edit_field_"))
async def process_edit_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[2]
    await state.update_data(field=field)
    if field == "text":
        await callback.message.edit_text("Введи новое название:")
        await state.set_state(EditTask.waiting_for_new_value)
    elif field == "category":
        keyboard = KeyboardBuilder.create_category_keyboard(callback.from_user.id, for_add=False)
        await callback.message.edit_text("Выбери новую категорию:", reply_markup=keyboard)
        await state.set_state(EditTask.waiting_for_new_category)
    elif field == "deadline":
        keyboard = create_calendar()
        await callback.message.edit_text("Выбери новую дату:", reply_markup=keyboard)
        await state.set_state(EditTask.waiting_for_deadline_date)
    await callback.answer()

@router.message(EditTask.waiting_for_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    value = message.text.strip()
    if not value or len(value) > 200:
        await message.reply("Значение не может быть пустым или слишком длинным.")
        return
    data = await state.get_data()
    task_id = data['task_id']
    field = data['field']
    edit_kwargs = {field: value}
    if task_manager.edit_task(task_id, **edit_kwargs):
        await message.reply("Задача обновлена!")
    else:
        await message.reply("Ошибка обновления.")
    await state.clear()

@router.callback_query(EditTask.waiting_for_new_category, lambda c: c.data.startswith("cat_"))
async def process_new_category_edit(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.replace("cat_", "")
    data = await state.get_data()
    task_id = data['task_id']
    if task_manager.edit_task(task_id, category=category):
        await callback.message.edit_text("Категория обновлена!")
    else:
        await callback.message.edit_text("Ошибка.")
    await state.clear()
    await callback.answer()

@router.callback_query(EditTask.waiting_for_deadline_date, lambda c: c.data.startswith("day_") or c.data.startswith("prev_month_") or c.data.startswith("next_month_"))
async def process_edit_date(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data.startswith("prev_month_") or data.startswith("next_month_"):
        parts = data.split("_")
        year = int(parts[2])
        month = int(parts[3])
        if data.startswith("prev_month_"):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        else:
            month += 1
            if month == 13:
                month = 1
                year += 1
        keyboard = create_calendar(year, month)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
        return
    if data == "skip_deadline":
        await save_edit_deadline(callback, state, None)
        return
    parts = data.split("_")
    year, month, day = int(parts[1]), int(parts[2]), int(parts[3])
    await state.update_data(date_str=f"{day:02d}.{month:02d}.{year}")
    keyboard = create_time_picker()
    await callback.message.edit_text("Выбери время:", reply_markup=keyboard)
    await state.set_state(EditTask.waiting_for_deadline_time)

@router.callback_query(EditTask.waiting_for_deadline_time, lambda c: c.data.startswith("time_") or c.data == "skip_deadline")
async def process_edit_time(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "skip_deadline":
        await save_edit_deadline(callback, state, None)
        return
    time_str = data.split("_")[1]
    data = await state.get_data()
    date_str = data.get("date_str")
    deadline = f"{date_str} {time_str}" if date_str else None
    await save_edit_deadline(callback, state, deadline)

async def save_edit_deadline(callback: types.CallbackQuery, state: FSMContext, deadline: Optional[str]):
    data = await state.get_data()
    task_id = data['task_id']
    if task_manager.edit_task(task_id, deadline=deadline):
        await callback.message.edit_text("Дедлайн обновлен!")
    else:
        await callback.message.edit_text("Ошибка обновления.")
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data == "cmd_stats")
async def stats_command(callback: types.CallbackQuery):
    data = task_manager.get_stats(callback.from_user.id, 30)
    plot_file = generate_stats_plot(data, callback.from_user.id)
    if plot_file:
        await callback.message.reply_photo(types.FSInputFile(plot_file))
        os.remove(plot_file)
    else:
        await callback.message.edit_text("Нет данных для статистики.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "cmd_export")
async def export_command(callback: types.CallbackQuery):
    filename = task_manager.export_to_csv(callback.from_user.id)
    if filename:
        await callback.message.reply_document(types.FSInputFile(filename))
        os.remove(filename)
    else:
        await callback.message.edit_text("Нет задач для экспорта.")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("page_"))
async def process_page_callback(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]
    page = int(parts[2])
    category = parts[3] if len(parts) > 3 else None
    completed = 0 if action in ["view", "done", "edit_select"] else 0
    tasks = task_manager.get_tasks(callback.from_user.id, completed=completed, category=category)
    keyboard = KeyboardBuilder.create_task_keyboard(tasks, page, action, category)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()