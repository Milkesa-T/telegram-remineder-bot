from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Returns the persistent main menu keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="➕ Create Reminder"),
        KeyboardButton(text="📋 My Reminders")
    )
    builder.row(
        KeyboardButton(text="⚙️ Timezone"),
        KeyboardButton(text="❓ Help")
    )
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Choose an option...")

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Returns a keyboard to cancel a current FSM flow."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Cancel"))
    return builder.as_markup(resize_keyboard=True)

def get_timezone_inline_keyboard() -> InlineKeyboardMarkup:
    """Returns inline buttons for popular timezones."""
    builder = InlineKeyboardBuilder()
    common_tzs = [
        ("UTC (GMT)", "UTC"),
        ("New York", "America/New_York"),
        ("London", "Europe/London"),
        ("Berlin", "Europe/Berlin"),
        ("Moscow", "Europe/Moscow"),
        ("New Delhi", "Asia/Kolkata"),
        ("Tokyo", "Asia/Tokyo"),
        ("Nairobi", "Africa/Nairobi"),
    ]
    for label, tz_code in common_tzs:
        builder.button(text=label, callback_data=f"set_tz:{tz_code}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✏️ Search / Type Zone...", callback_data="type_tz"))
    return builder.as_markup()

def get_reminder_list_keyboard(reminders: list) -> InlineKeyboardMarkup:
    """Generates inline delete buttons for a user's reminders list."""
    builder = InlineKeyboardBuilder()
    for idx, rem in enumerate(reminders, start=1):
        builder.button(text=f"❌ Delete {idx}", callback_data=f"del_rem:{rem.id}")
    builder.adjust(3)
    return builder.as_markup()
