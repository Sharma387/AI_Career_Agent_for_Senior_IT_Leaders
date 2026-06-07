"""
Timezone utilities for handling New Zealand time conversions.
"""
import pytz
from datetime import datetime, time
from typing import Tuple


def get_nz_time() -> datetime:
    """
    Get current time in New Zealand timezone.

    Returns:
        datetime: Current time in NZ timezone
    """
    nz_tz = pytz.timezone('Pacific/Auckland')
    return datetime.now(nz_tz)


def is_business_hours_nz(start_hour: int = 6, end_hour: int = 22) -> bool:
    """
    Check if current NZ time is within business hours.

    Args:
        start_hour: Start hour in 24-hour format (default 6 AM)
        end_hour: End hour in 24-hour format (default 10 PM)

    Returns:
        bool: True if within business hours, False otherwise
    """
    nz_time = get_nz_time()
    current_hour = nz_time.hour
    return start_hour <= current_hour < end_hour


def get_nz_time_components() -> Tuple[int, int, int]:
    """
    Get hour, minute, second components of current NZ time.

    Returns:
        Tuple of (hour, minute, second)
    """
    nz_time = get_nz_time()
    return nz_time.hour, nz_time.minute, nz_time.second


def is_time_for_full_scrape(target_hour: int = 6, target_minute: int = 0) -> bool:
    """
    Check if current NZ time matches the target time for full scrape.

    Args:
        target_hour: Target hour in 24-hour format (default 6 AM)
        target_minute: Target minute (default 0)

    Returns:
        bool: True if current time matches target time within a minute window
    """
    nz_time = get_nz_time()
    # Allow a 2-minute window to account for slight timing differences
    return (nz_time.hour == target_hour and
            abs(nz_time.minute - target_minute) <= 1)