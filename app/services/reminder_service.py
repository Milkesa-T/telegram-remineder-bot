from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import User, Reminder
from app.config.config import logger

async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None
) -> User:
    """Fetch user by ID or create if not exists."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            timezone="UTC"  # Default timezone
        )
        session.add(user)
        await session.flush()  # Make user available in session before commit
        logger.info(f"Created new user profile: {user}")
    else:
        # Check if details have changed
        updated = False
        if user.username != username:
            user.username = username
            updated = True
        if user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if user.last_name != last_name:
            user.last_name = last_name
            updated = True
        if updated:
            session.add(user)
            await session.flush()
            logger.info(f"Updated profile details for user: {user}")

    return user

async def update_user_timezone(session: AsyncSession, user_id: int, timezone: str) -> None:
    """Update user's local timezone."""
    stmt = update(User).where(User.id == user_id).values(timezone=timezone)
    await session.execute(stmt)
    logger.info(f"Updated timezone to {timezone} for user_id={user_id}")

async def create_reminder(
    session: AsyncSession,
    user_id: int,
    title: str,
    trigger_at: datetime
) -> Reminder:
    """Save a new reminder to the database."""
    reminder = Reminder(
        user_id=user_id,
        title=title,
        trigger_at=trigger_at
    )
    session.add(reminder)
    await session.flush()
    logger.info(f"Saved new reminder to DB: {reminder}")
    return reminder

async def get_active_reminders(session: AsyncSession, user_id: int) -> list[Reminder]:
    """Get active (un-triggered, non-cancelled) reminders for a user."""
    stmt = (
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.is_triggered == False,
            Reminder.is_cancelled == False
        )
        .order_by(Reminder.trigger_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_reminder_by_id(session: AsyncSession, reminder_id: int) -> Reminder | None:
    """Retrieve a single reminder by ID."""
    stmt = select(Reminder).where(Reminder.id == reminder_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def mark_reminder_triggered(session: AsyncSession, reminder_id: int) -> None:
    """Mark a reminder as triggered."""
    stmt = update(Reminder).where(Reminder.id == reminder_id).values(is_triggered=True)
    await session.execute(stmt)
    logger.info(f"Reminder {reminder_id} marked as triggered in database.")

async def cancel_reminder(session: AsyncSession, reminder_id: int) -> bool:
    """Cancel a pending reminder."""
    # Check if the reminder is active first
    reminder = await get_reminder_by_id(session, reminder_id)
    if reminder and not reminder.is_triggered and not reminder.is_cancelled:
        reminder.is_cancelled = True
        session.add(reminder)
        await session.flush()
        logger.info(f"Reminder {reminder_id} cancelled in database.")
        return True
    return False

async def get_all_pending_reminders(session: AsyncSession) -> list[Reminder]:
    """Get all non-triggered, non-cancelled reminders across all users."""
    stmt = (
        select(Reminder)
        .where(
            Reminder.is_triggered == False,
            Reminder.is_cancelled == False
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
