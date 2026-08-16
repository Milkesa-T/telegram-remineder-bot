import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config.config import settings, logger
from app.database.connection import engine
from app.database.models import Base
from app.services.scheduler import scheduler, restore_pending_reminders
from app.handlers import common, timezone, reminders

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    """Lifecycle hook called when the bot starts polling."""
    logger.info("Starting Telegram Reminder Bot lifecycle...")
    
    # 1. Initialize database tables
    logger.info("Creating database tables if they do not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")

    # 2. Restore active reminders and load them into APScheduler
    await restore_pending_reminders(bot)

    # 3. Start the scheduler
    scheduler.start()
    logger.info("APScheduler background jobs engine started.")

async def on_shutdown(dispatcher: Dispatcher):
    """Lifecycle hook called when the bot is shutting down."""
    logger.info("Shutting down Telegram Reminder Bot...")
    
    # 1. Shutdown scheduler
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")
    
    # 2. Dispose of SQLAlchemy async database engine
    await engine.dispose()
    logger.info("SQLAlchemy connection pool disposed.")

async def main():
    # Verify bot token is configured
    if not settings.bot_token or settings.bot_token == "your_telegram_bot_token_here":
        logger.critical(
            "\n"
            "===================================================================\n"
            " ERROR: BOT_TOKEN is not configured!\n"
            " Please create a '.env' file based on '.env.example' and insert\n"
            " your actual Telegram Bot Token from @BotFather.\n"
            "===================================================================\n"
        )
        sys.exit(1)

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Include bot routers
    dp.include_router(common.router)
    dp.include_router(timezone.router)
    dp.include_router(reminders.router)

    # Register startup and shutdown lifecycle events
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start the asyncio polling event loop
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process interrupted by user. Exited.")
