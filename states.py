from aiogram.fsm.state import State, StatesGroup

class AddTask(StatesGroup):
    waiting_for_category = State()
    waiting_for_new_category = State()
    waiting_for_task = State()
    waiting_for_deadline_date = State()
    waiting_for_deadline_time = State()

class EditTask(StatesGroup):
    waiting_for_task = State()
    waiting_for_field = State()
    waiting_for_new_value = State()
    waiting_for_new_category = State()
    waiting_for_deadline_date = State()
    waiting_for_deadline_time = State()

class SubtaskStates(StatesGroup):
    waiting_for_subtask = State()