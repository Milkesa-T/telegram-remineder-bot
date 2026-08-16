from datetime import datetime
import zoneinfo
import dateparser
from app.config.config import logger

def parse_user_time(text: str, user_tz_str: str) -> datetime | None:
    """
    Parses a user time input (e.g. 'in 2 hours', 'tomorrow at 9:00 am', 'at 18:30')
    in the context of the user's timezone, and returns a UTC timezone-aware datetime object.
    
    Returns None if parsing fails.
    """
    try:
        # Retrieve timezone
        tz = zoneinfo.ZoneInfo(user_tz_str)
    except Exception as e:
        logger.error(f"Invalid timezone: {user_tz_str}. Error: {e}")
        tz = zoneinfo.ZoneInfo("UTC")

    # Get local current time
    now_local = datetime.now(tz)
    
    # Use naive local datetime as relative base for dateparser
    now_local_naive = now_local.replace(tzinfo=None)

    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": now_local_naive,
        "TIMEZONE": user_tz_str,
        "RETURN_AS_TIMEZONE_AWARE": True,
    }

    try:
        parsed_dt = dateparser.parse(text, settings=settings)
        if not parsed_dt:
            # Let's try some simple custom parsing if dateparser fails
            # e.g. "5m" -> "in 5 minutes"
            cleaned_text = text.strip().lower()
            if cleaned_text.endswith("m") and cleaned_text[:-1].isdigit():
                text = f"in {cleaned_text[:-1]} minutes"
            elif cleaned_text.endswith("h") and cleaned_text[:-1].isdigit():
                text = f"in {cleaned_text[:-1]} hours"
            elif cleaned_text.endswith("d") and cleaned_text[:-1].isdigit():
                text = f"in {cleaned_text[:-1]} days"
                
            parsed_dt = dateparser.parse(text, settings=settings)
            
        if not parsed_dt:
            return None

        # Convert to UTC-aware datetime
        utc_dt = parsed_dt.astimezone(zoneinfo.ZoneInfo("UTC"))
        return utc_dt
    except Exception as e:
        logger.error(f"Error parsing time text '{text}': {e}")
        return None
