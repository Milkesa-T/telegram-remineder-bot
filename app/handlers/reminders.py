from datetime import datetime, timezone
import zoneinfo
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.utils.states import ReminderStates
from app.utils.keyboards import (
    get_cancel_keyboard, 
    get_main_keyboard, 
    get_reminder_list_keyboard
)
from app.utils.time_parser import parse_user_time
from app.database.connection import AsyncSessionLocal
from app.services import reminder_service
from app.services.scheduler import schedule_reminder_job, unschedule_reminder_job
from app.config.config import logger

router = Router()

def parse_quick_reminder(text: str, user_tz: str) -> tuple[str, datetime] | None:
    """
    Attempts to split a natural language text command (e.g. 'Call Mom in 2 hours')
    into a reminder title and a future trigger datetime.
    
    Uses a right-to-left scanning heuristic to find the longest time expression.
    """
    words = text.strip().split()
    if len(words) < 2:
        return None

    # Scan from left to right to find where the time expression begins.
    # E.g., for "Call Mom in 2 hours", words are:
    # 0: Call, 1: Mom, 2: in, 3: 2, 4: hours
    # We test:
    # i=1: "Mom in 2 hours" -> parses?
    # i=2: "in 2 hours" -> parses! -> title is "Call Mom"
    now_utc = datetime.now(timezone.utc)
    for i in range(1, len(words)):
        time_part = " ".join(words[i:])
        title_part = " ".join(words[:i])
        
        parsed_dt = parse_user_time(time_part, user_tz)
        if parsed_dt and parsed_dt > now_utc:
            return title_part, parsed_dt

    return None

async def send_reminder_list(message: Message, user_id: int, edit_message: Message = None):
    """Utility to fetch and format active reminders for a user."""
    async with AsyncSessionLocal() as session:
        user = await reminder_service.get_or_create_user(session, user_id)
        reminders = await reminder_service.get_active_reminders(session, user_id)
        user_tz = user.timezone

    if not reminders:
        text = "📋 <b>You have no active reminders.</b>\n\nCreate one by typing /remind or clicking ➕ <b>Create Reminder</b> below!"
        if edit_message:
            await edit_message.edit_text(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())
        return

    tz = zoneinfo.ZoneInfo(user_tz)
    lines = ["📋 <b>Your Active Reminders:</b>\n"]
    for idx, rem in enumerate(reminders, start=1):
        # Convert UTC trigger time to user local time for display
        local_trigger = rem.trigger_at.astimezone(tz)
        time_str = local_trigger.strftime("%Y-%m-%d %I:%M %p")
        lines.append(f"{idx}. ⏰ <b>{rem.title}</b>\n   📅 {time_str} ({user_tz})")

    lines.append("\n💡 <i>To delete a reminder, click the corresponding button below.</i>")
    full_text = "\n".join(lines)

    if edit_message:
        await edit_message.edit_text(
            full_text, 
            parse_mode="HTML", 
            reply_markup=get_reminder_list_keyboard(reminders)
        )
    else:
        await message.answer(
            full_text, 
            parse_mode="HTML", 
            reply_markup=get_reminder_list_keyboard(reminders)
        )

# ----------------- QUICK REMINDER HANDLER -----------------

@router.message(Command("remind"))
async def cmd_remind_quick(message: Message, command: CommandObject, bot: Bot, state: FSMContext):
    """Handles the /remind command. Supports quick syntax or starts interactive flow if empty."""
    user_id = message.from_user.id
    
    # Check user and timezone first
    async with AsyncSessionLocal() as session:
        user = await reminder_service.get_or_create_user(
            session, 
            user_id, 
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        user_tz = user.timezone

    # If no arguments, fallback to interactive mode
    if not command.args:
        await state.set_state(ReminderStates.waiting_for_title)
        await message.answer(
            "➕ <b>Create Reminder</b>\n\n"
            "What would you like to be reminded about? (e.g. 'Take the cake out of the oven')",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Try parsing quick syntax
    parsed = parse_quick_reminder(command.args, user_tz)
    if not parsed:
        await message.answer(
            "❌ <b>Could not parse reminder details.</b>\n\n"
            "Please use format: <code>/remind [task] [time]</code>\n"
            "<i>Example:</i> <code>/remind Check mail in 30 minutes</code>\n\n"
            "Or tap ➕ <b>Create Reminder</b> to use the guided wizard.",
            parse_mode="HTML"
        )
        return

    title, trigger_at = parsed
    
    async with AsyncSessionLocal() as session:
        # 1. Save to Database
        reminder = await reminder_service.create_reminder(session, user_id, title, trigger_at)
        await session.commit()
        
        # 2. Schedule APScheduler Job
        schedule_reminder_job(reminder.id, trigger_at, bot)
        
    # Format trigger time back to local time for user feedback
    tz = zoneinfo.ZoneInfo(user_tz)
    local_trigger = trigger_at.astimezone(tz)
    local_str = local_trigger.strftime("%Y-%m-%d %I:%M %p")

    await message.answer(
        f"✅ <b>Reminder set successfully!</b>\n\n"
        f"📝 <b>Task:</b> {title}\n"
        f"📅 <b>When:</b> {local_str} ({user_tz})",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


# ----------------- INTERACTIVE WIZARD FLOW -----------------

@router.message(F.text == "➕ Create Reminder")
async def start_interactive_reminder(message: Message, state: FSMContext):
    """Starts FSM wizard for reminder creation."""
    user_id = message.from_user.id
    # Register/fetch user to ensure they exist
    async with AsyncSessionLocal() as session:
        await reminder_service.get_or_create_user(
            session, 
            user_id, 
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )

    await state.set_state(ReminderStates.waiting_for_title)
    await message.answer(
        "➕ <b>Create Reminder</b>\n\n"
        "What would you like to be reminded about?",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(ReminderStates.waiting_for_title)
async def process_reminder_title(message: Message, state: FSMContext):
    """Receives and saves reminder title."""
    title = message.text.strip()
    if not title:
        await message.answer("⚠️ Title cannot be empty. Please type the reminder title:")
        return
        
    await state.update_data(title=title)
    await state.set_state(ReminderStates.waiting_for_time)
    await message.answer(
        f"⏰ <b>Great! When should I remind you?</b>\n\n"
        f"You can specify a relative or absolute time, such as:\n"
        f"• <code>in 15 mins</code>\n"
        f"• <code>in 3 hours</code>\n"
        f"• <code>tomorrow at 9 am</code>\n"
        f"• <code>at 18:30</code>\n"
        f"• <code>monday at 12:00</code>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(ReminderStates.waiting_for_time)
async def process_reminder_time(message: Message, state: FSMContext, bot: Bot):
    """Receives, parses time, saves to DB, schedules job, and completes flow."""
    time_text = message.text.strip()
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user = await reminder_service.get_or_create_user(session, user_id)
        user_tz = user.timezone

    trigger_at = parse_user_time(time_text, user_tz)
    if not trigger_at:
        await message.answer(
            f"❌ <b>Could not parse time format '{time_text}'.</b>\n\n"
            f"Please try again (e.g., 'in 2 hours', 'tomorrow at 3 pm', 'at 18:30') or click ❌ Cancel:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    now_utc = datetime.now(timezone.utc)
    if trigger_at <= now_utc:
        await message.answer(
            "⚠️ <b>Specified time is in the past!</b>\n\n"
            "Please specify a future date/time:",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Retrieve title from FSM
    data = await state.get_data()
    title = data.get("title")

    async with AsyncSessionLocal() as session:
        # Save reminder to database
        reminder = await reminder_service.create_reminder(session, user_id, title, trigger_at)
        await session.commit()
        
        # Schedule the background trigger job
        schedule_reminder_job(reminder.id, trigger_at, bot)

    await state.clear()

    # Format local time to print back to user
    tz = zoneinfo.ZoneInfo(user_tz)
    local_trigger = trigger_at.astimezone(tz)
    local_str = local_trigger.strftime("%Y-%m-%d %I:%M %p")

    await message.answer(
        f"✅ <b>Reminder set successfully!</b>\n\n"
        f"📝 <b>Task:</b> {title}\n"
        f"📅 <b>When:</b> {local_str} ({user_tz})",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


# ----------------- LIST & DELETE REMINDERS -----------------

@router.message(Command("list"))
@router.message(F.text == "📋 My Reminders")
async def cmd_list_reminders(message: Message):
    """Lists user's active reminders with delete buttons."""
    await send_reminder_list(message, message.from_user.id)

@router.callback_query(F.data.startswith("del_rem:"))
async def cb_delete_reminder(callback: CallbackQuery):
    """Deletes/cancels a reminder from the DB and active scheduler."""
    reminder_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        # Cancel in DB
        success = await reminder_service.cancel_reminder(session, reminder_id)
        if success:
            await session.commit()
            # Cancel in scheduler
            unschedule_reminder_job(reminder_id)
            await callback.answer("✅ Reminder cancelled!")
        else:
            await callback.answer("⚠️ Reminder already triggered or not found.", show_alert=True)

    # Re-render list
    await send_reminder_list(callback.message, user_id, edit_message=callback.message)
