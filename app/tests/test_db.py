import sys
import asyncio
from datetime import datetime, timezone

# Add the project directory to sys.path
project_dir = r"c:\Users\SPECTRE\AI-Automation\telegram-reminder-bot"
sys.path.insert(0, project_dir)

from app.config.config import settings
from app.database.connection import engine, AsyncSessionLocal
from app.database.models import Base, User, Reminder
from sqlalchemy import select, delete

async def test_db_connection():
    print("=== Database Connection & Setup Validation ===")
    print(f"Connecting to: {settings.database_url}")
    print("---------------------------------------------")

    try:
        # 1. Create tables
        async with engine.begin() as conn:
            print("Creating database tables if not exist...")
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created/verified successfully!")

        # 2. Perform CRUD inside a proper async session
        async with AsyncSessionLocal() as session:
            test_user_id = 999999999

            # Clean up any old test user
            await session.execute(delete(User).where(User.id == test_user_id))
            await session.commit()

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

            # Retrieve reminders
            result = await session.execute(
                select(Reminder).where(Reminder.user_id == test_user_id)
            )
            loaded = result.scalars().all()
            print(f"Fetched {len(loaded)} reminder(s) from database for test user.")
            for r in loaded:
                print(f"  - [{r.id}] '{r.title}', trigger_at: {r.trigger_at}")

            # Cleanup
            print("Cleaning up test data...")
            await session.execute(delete(User).where(User.id == test_user_id))
            await session.commit()
            print("Cleanup completed successfully.")

        print("\n✅ DATABASE INTEGRITY TEST: PASSED")

    except Exception as e:
        print(f"\n❌ DATABASE INTEGRITY TEST: FAILED")
        print(f"Error Details: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_db_connection())
