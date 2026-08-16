from aiogram.fsm.state import StatesGroup, State

class ReminderStates(StatesGroup):
    waiting_for_title = State()  # Waiting for the reminder message content
    waiting_for_time = State()   # Waiting for the trigger time/date

class TimezoneStates(StatesGroup):
    waiting_for_timezone = State()  # Waiting for the user to pick/type their timezone
