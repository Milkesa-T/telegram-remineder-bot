from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from app.utils.keyboards import get_main_keyboard
from app.database.connection import AsyncSessionLocal
from app.services import reminder_service

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handles the /start command. Registers the user and displays welcome info."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    async with AsyncSessionLocal() as session:
        user = await reminder_service.get_or_create_user(
            session=session,
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        await session.commit()

    welcome_text = (
        f"👋 Hello, <b>{first_name or 'there'}</b>!\n\n"
        f"I'm a modern <b>Telegram Reminder Bot</b>. I'll help you keep track of all your tasks and remind you exactly when they need to be done.\n\n"
        f"🌐 Your default timezone is set to <b>{user.timezone}</b>.\n"
        f"💡 You can change this anytime under the ⚙️ <b>Timezone</b> menu.\n\n"
        f"<b>To set a reminder:</b>\n"
        f"• Use the ➕ <b>Create Reminder</b> button below.\n"
        f"• Or send <code>/remind [your task] in 10 minutes</code>\n"
        f"• Or send <code>/remind [your task] tomorrow at 9 am</code>"
    )
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_keyboard())

@router.message(Command("help"))
@router.message(F.text == "❓ Help")
async def cmd_help(message: Message):
    """Displays help text."""
    help_text = (
        f"🤖 <b>Reminder Bot Help</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Commands:</b>\n"
        f"• /start - Restart the bot and show greeting\n"
        f"• /help - Display this help message\n"
        f"• /timezone - Choose or search your local timezone\n"
        f"• /list - List your active reminders\n"
        f"• /remind [task] [time] - Quick reminder creation\n"
        f"  <i>Examples:</i>\n"
        f"  - <code>/remind Call Mom in 45m</code>\n"
        f"  - <code>/remind Buy coffee tomorrow at 10:15 am</code>\n"
        f"  - <code>/remind Go to gym at 21:00</code>\n\n"
        f"<b>Interactive Features:</b>\n"
        f"• ➕ <b>Create Reminder</b> - Step-by-step reminder builder.\n"
        f"• 📋 <b>My Reminders</b> - List all active reminders. You can delete or cancel reminders using the inline buttons.\n"
        f"• ⚙️ <b>Timezone</b> - Set your local timezone to ensure reminders trigger at your local time."
    )
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())

@router.message(Command("cancel"))
@router.message(F.text == "❌ Cancel")
async def cmd_cancel(message: Message, state: FSMContext):
    """Cancels any current dialog state (FSM) and returns to main menu."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    await message.answer(
        "❌ Action cancelled. Returned to main menu.",
        reply_markup=get_main_keyboard()
    )
