import zoneinfo
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.utils.states import TimezoneStates
from app.utils.keyboards import get_timezone_inline_keyboard, get_cancel_keyboard, get_main_keyboard
from app.database.connection import AsyncSessionLocal
from app.services import reminder_service
from app.config.config import logger

router = Router()

def find_timezone(query: str) -> str | None:
    """
    Finds a timezone code based on user search query.
    Looks for exact match, city match, or substring match in available timezones.
    """
    normalized_query = query.strip().lower().replace(" ", "_")
    
    # Try retrieving all system timezones
    try:
        # available_timezones requires tzdata on Windows
        zones = zoneinfo.available_timezones()
    except Exception:
        # Fallback list of common timezones if available_timezones fails
        zones = {
            "UTC", "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Rome", 
            "Europe/Madrid", "Europe/Moscow", "Europe/Istanbul", "Europe/Kiev",
            "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", 
            "America/Sao_Paulo", "America/Argentina/Buenos_Aires", "America/Mexico_City",
            "Asia/Kolkata", "Asia/Tokyo", "Asia/Shanghai", "Asia/Singapore", 
            "Asia/Seoul", "Asia/Dubai", "Asia/Jakarta", "Asia/Hong_Kong",
            "Africa/Nairobi", "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos", 
            "Africa/Casablanca", "Australia/Sydney", "Australia/Melbourne", 
            "Australia/Perth", "Pacific/Auckland", "Pacific/Honolulu"
        }

    # 1. Check exact match
    for zone in zones:
        if zone.lower() == normalized_query:
            return zone

    # 2. Check suffix/city match (e.g., "nairobi" -> "Africa/Nairobi")
    for zone in zones:
        parts = zone.lower().split("/")
        if normalized_query == parts[-1]:
            return zone

    # 3. Check substring match in any part of the path
    for zone in zones:
        if normalized_query in zone.lower():
            return zone

    return None

async def show_timezone_menu(message: Message, user_tz: str):
    """Utility to display the timezone configuration menu."""
    text = (
        f"🌐 <b>Timezone Configuration</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Your current timezone is: <b>{user_tz}</b>\n\n"
        f"To ensure reminders are sent at the correct time, please choose your timezone from the options below or tap <b>Search</b> to enter your location."
    )
    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=get_timezone_inline_keyboard()
    )

@router.message(Command("timezone"))
@router.message(F.text == "⚙️ Timezone")
async def cmd_timezone(message: Message):
    """Handles the timezone settings request."""
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = await reminder_service.get_or_create_user(session, user_id)
        current_tz = user.timezone
    await show_timezone_menu(message, current_tz)

@router.callback_query(F.data.startswith("set_tz:"))
async def cb_set_timezone(callback: CallbackQuery):
    """Sets timezone from popular selection buttons."""
    tz_code = callback.data.split(":")[1]
    user_id = callback.from_user.id

    try:
        zoneinfo.ZoneInfo(tz_code)
    except Exception:
        await callback.answer("⚠️ Invalid timezone selection.", show_alert=True)
        return

    async with AsyncSessionLocal() as session:
        await reminder_service.update_user_timezone(session, user_id, tz_code)
        await session.commit()

    await callback.answer("✅ Timezone updated!")
    await callback.message.edit_text(
        f"✅ <b>Timezone successfully set to:</b> {tz_code}\n\n"
        f"Your reminders will now trigger relative to this timezone.",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "type_tz")
async def cb_type_timezone(callback: CallbackQuery, state: FSMContext):
    """Prompts the user to type a timezone query."""
    await state.set_state(TimezoneStates.waiting_for_timezone)
    await callback.message.delete()
    await callback.message.answer(
        "📝 Please type your <b>City name</b> or <b>Timezone code</b>:\n\n"
        "<i>Examples:</i>\n"
        "• <code>Nairobi</code>\n"
        "• <code>New York</code>\n"
        "• <code>Europe/London</code>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(TimezoneStates.waiting_for_timezone)
async def process_typed_timezone(message: Message, state: FSMContext):
    """Processes search query and updates timezone if unique match found."""
    query = message.text
    matched_tz = find_timezone(query)

    if not matched_tz:
        await message.answer(
            f"❌ Timezone matching <b>'{query}'</b> was not found.\n"
            f"Please try another city name or code (or tap ❌ Cancel):",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        await reminder_service.update_user_timezone(session, user_id, matched_tz)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ <b>Timezone successfully set to:</b> {matched_tz}\n\n"
        f"Reminders will now trigger relative to this timezone.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
