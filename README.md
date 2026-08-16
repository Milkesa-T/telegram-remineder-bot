# Modern Telegram Reminder Bot

An asynchronous, professional, and robust Telegram Reminder Bot built with **Python (aiogram 3.x)**, **PostgreSQL (SQLAlchemy 2.0 + asyncpg)**, and **APScheduler**.

## Features

- **Dynamic Job Scheduling**: Reminders are scheduled in-memory and automatically persisted to a PostgreSQL database.
- **Bot Restart Resilience**: If the bot restarts, it recovers all active reminders from the database. Any reminders missed while the bot was offline trigger immediately.
- **Guided Creation Flow**: An interactive step-by-step FSM wizard to easily create new reminders.
- **Natural Language Parsing**: Create quick reminders with commands like:
  - `/remind Go to gym in 45 minutes`
  - `/remind Buy groceries tomorrow at 9 am`
  - `/remind Stand up at 18:30`
- **Timezone Customization**: Set your local timezone (e.g. `America/New_York`, `Europe/London`, `Africa/Nairobi`) so that relative and absolute time triggers align precisely with your local clock.
- **Reminder Listing & Cancellation**: View your pending reminders with inline buttons to cancel/delete them.

---

## Technical Architecture

- **`aiogram` (v3.x)**: High-performance asynchronous Telegram Bot API framework.
- **SQLAlchemy (v2.0)**: Modern declarative mapping for database schemas.
- **`asyncpg`**: Fastest asynchronous Python driver for PostgreSQL.
- **APScheduler**: Thread-safe asynchronous scheduler for executing database-triggered callback notifications.
- **`dateparser`**: Sophisticated text-to-datetime parser for local timezones.
- **Docker Compose**: Containerized environment for local database setup.

---

## Setup Instructions

### 1. Prerequisites
- **Python 3.10+** (Python 3.13 is recommended and pre-configured).
- **PostgreSQL Database** (either running locally, on a server, or via Docker).
- **Telegram Bot Token**: Get a token by messaging [@BotFather](https://t.me/BotFather) on Telegram.

### 2. Configure Environment
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your configuration:
   ```env
   BOT_TOKEN=your_actual_telegram_bot_token_here
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reminder_bot
   ```

### 3. Spin up PostgreSQL Database (Optional via Docker Compose)
If you have Docker installed, you can start a PostgreSQL container with:
```bash
docker-compose up -d
```
*Note: If you have PostgreSQL installed on your system directly, ensure it is running and create a database named `reminder_bot` with the credentials specified in your `.env`.*

### 4. Install Dependencies
A virtual environment `.venv` is already configured in the repository. Activate it and install dependencies:
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- **Linux/macOS**:
  ```bash
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

---

## Running the Bot

Run the bot main entrypoint:
```bash
python main.py
```
*Upon startup, the bot will automatically verify and create all database tables in PostgreSQL if they do not exist, load any pending scheduled jobs, and start polling Telegram.*

---

## Bot Interaction

Search for your bot username on Telegram, click **Start**, and enjoy your modern assistant!

### Menu Actions
- ➕ **Create Reminder**: Start the step-by-step wizard.
- 📋 **My Reminders**: View active reminders list and cancel them.
- ⚙️ **Timezone**: View and update your timezone via search or popular buttons.
- ❓ **Help**: Display all supported syntax rules and commands.
