import sys
import asyncio
from datetime import datetime, timezone

# Add the project directory to sys.path
project_dir = r"c:\Users\SPECTRE\AI-Automation\telegram-reminder-bot"
sys.path.insert(0, project_dir)

from app.config.config import settings, logger
from app.database.connection import engine
from app.database.models import Base, User, Reminder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def test_db_connection():
    print("=== Database Connection & Setup Validation ===")
    print(f"Connecting to: {settings.database_url}")
    print("---------------------------------------------")
    
    try:
        # 1. Attempt connection and table creation
        async with engine.begin() as conn:
            print("Creating database tables if not exist...")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created/verified successfully!")

        # 2. Try creating a session and doing basic CRUD
        async with AsyncSession(engine) as session:
            # Let's clean up test user if exists
            test_user_id = 999999999
            stmt = select(User).where(User.id == test_user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                print("Found old test user. Deleting...")
                await session.delete(user)
                await session.commit()
                print("Old test user deleted.")

            # Create test user
            print("Adding a test user...")
            new_user = User(
                id=test_user_id,
                username="db_test_user",
                first_name="DB Test",
                last_name="Runner",
                timezone="America/New_York"
            )
            session.add(new_user)
            await session.commit()
            print(f"User added: {new_user}")

            # Create test reminder
            print("Adding a test reminder for user...")
            new_reminder = Reminder(
                user_id=test_user_id,
                title="Verify Database Setup",
                trigger_at=datetime.now(timezone.utc)
            )
            session.add(new_reminder)
            await session.commit()
            print(f"Reminder added: {new_reminder}")

            # Retrieve reminder
            stmt = select(Reminder).where(Reminder.user_id == test_user_id)
            result = await session.execute(stmt)
            loaded_reminders = result.scalars().all()
            print(f"Fetched {len(loaded_reminders)} reminders from database for test user.")
            for r in loaded_reminders:
                print(f"  - [{r.id}] title: '{r.title}', trigger_at: {r.trigger_at}")

            # Clean up test user (will cascade delete reminder)
            print("Cleaning up test user & reminder...")
            await session.delete(new_user)
            await session.commit()
            print("Cleanup completed successfully.")
            
        print("\nDATABASE INTEGRITY TEST: SUCCESS")
    except Exception as e:
        print("\nDATABASE INTEGRITY TEST: FAILED")
        print(f"Error Details: {e}")
        print("\nSuggestion: Make sure your PostgreSQL server is running and the credentials in '.env' are correct.")

if __name__ == "__main__":
    asyncio.run(test_db_connection())
