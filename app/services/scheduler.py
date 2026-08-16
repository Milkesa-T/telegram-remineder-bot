from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from app.database.connection import AsyncSessionLocal
from app.services import reminder_service
from app.config.config import logger

# Initialize AsyncIOScheduler
scheduler = AsyncIOScheduler()

async def fire_reminder(reminder_id: int, bot: Bot):
    """
    Callback function that fires when a reminder scheduled job triggers.
    Sends the reminder message to the user and marks it as triggered in the DB.
    """
    logger.info(f"Fired scheduled job for reminder_id={reminder_id}")
    async with AsyncSessionLocal() as session:
        try:
            reminder = await reminder_service.get_reminder_by_id(session, reminder_id)
            if not reminder:
                logger.warning(f"Reminder {reminder_id} not found in database. Skipping.")
                return

            if reminder.is_cancelled:
                logger.info(f"Reminder {reminder_id} is cancelled. Skipping trigger.")
                return

            if reminder.is_triggered:
                logger.info(f"Reminder {reminder_id} was already triggered. Skipping.")
                return

            # Deliver reminder to the Telegram User
            message_text = (
                f"🔔 <b>REMINDER!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{reminder.title}\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            await bot.send_message(
                chat_id=reminder.user_id, 
                text=message_text, 
                parse_mode="HTML"
            )
            
            # Set triggered status
            await reminder_service.mark_reminder_triggered(session, reminder_id)
            await session.commit()
            logger.info(f"Successfully sent reminder {reminder_id} to user {reminder.user_id}.")

        except Exception as e:
            logger.error(f"Error handling trigger for reminder {reminder_id}: {e}", exc_info=True)
            await session.rollback()

def schedule_reminder_job(reminder_id: int, trigger_at: datetime, bot: Bot):
    """Schedules a future reminder trigger in the active scheduler."""
    job_id = f"reminder_{reminder_id}"
    
    # If a job with this ID already exists, remove it first
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        fire_reminder,
        trigger="date",
        run_date=trigger_at,
        args=[reminder_id, bot],
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"Scheduled job '{job_id}' to fire at {trigger_at} UTC")

def unschedule_reminder_job(reminder_id: int):
    """Removes a reminder job from the active scheduler."""
    job_id = f"reminder_{reminder_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed job '{job_id}' from scheduler")

async def restore_pending_reminders(bot: Bot):
    """
    On startup, load all active reminders from the database.
    - If the reminder time has passed, trigger it immediately (handling missed reminders).
    - If the reminder time is in the future, schedule it in the APScheduler.
    """
    logger.info("Restoring active reminders from database...")
    async with AsyncSessionLocal() as session:
        try:
            pending_list = await reminder_service.get_all_pending_reminders(session)
            now_utc = datetime.now(timezone.utc)
            
            for reminder in pending_list:
                if reminder.trigger_at <= now_utc:
                    # Reminder was missed while the bot was offline. Trigger immediately.
                    logger.warning(
                        f"Reminder {reminder.id} was missed (scheduled for {reminder.trigger_at} UTC). "
                        f"Triggering immediately."
                    )
                    scheduler.add_job(
                        fire_reminder,
                        args=[reminder.id, bot],
                        id=f"reminder_missed_{reminder.id}"
                    )
                else:
                    # Schedule future reminder
                    schedule_reminder_job(reminder.id, reminder.trigger_at, bot)
            
            logger.info(f"Restored and scheduled {len(pending_list)} pending reminders.")
        except Exception as e:
            logger.error(f"Failed to restore pending reminders: {e}", exc_info=True)
