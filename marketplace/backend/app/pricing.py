"""Calculate a meeting room quote from its rate and Oslo booking time."""

from datetime import UTC, datetime, timedelta
from typing import TypedDict
from zoneinfo import ZoneInfo


_OSLO = ZoneInfo("Europe/Oslo")


class PriceQuote(TypedDict):
    price_ore: int
    hourly_rate_ore: int
    base_hourly_rate_ore: int
    reason: str


def quote_price(
    *,
    hourly_rate_ore: int,
    minimum_hourly_rate_ore: int,
    maximum_hourly_rate_ore: int,
    start_at: datetime,
    duration_minutes: int,
    now: datetime,
) -> PriceQuote:
    """Apply time bands to the booking start and quote the requested duration."""
    if start_at.utcoffset() is None or now.utcoffset() is None:
        raise ValueError("Pricing timestamps must include a time zone")
    if duration_minutes < 1:
        raise ValueError("Booking duration must be positive")

    local_start = start_at.astimezone(_OSLO)
    if local_start.weekday() >= 5:
        time_percent, reason = 80, "Weekend rate (−20%)"
    elif 9 <= local_start.hour < 16:
        time_percent, reason = 120, "Weekday peak rate (+20%)"
    else:
        time_percent, reason = 85, "Weekday off-peak rate (−15%)"

    lead_time = start_at.astimezone(UTC) - now.astimezone(UTC)
    last_minute_percent = 100
    if timedelta(0) <= lead_time <= timedelta(minutes=30):
        last_minute_percent = 90
        reason += ". Last-minute discount (−10%)"

    adjusted_rate = (hourly_rate_ore * time_percent * last_minute_percent + 9_999) // 10_000
    if adjusted_rate < minimum_hourly_rate_ore:
        adjusted_rate = minimum_hourly_rate_ore
        reason += ". Room minimum applied"
    elif adjusted_rate > maximum_hourly_rate_ore:
        adjusted_rate = maximum_hourly_rate_ore
        reason += ". Room maximum applied"

    return {
        "price_ore": (adjusted_rate * duration_minutes + 59) // 60,
        "hourly_rate_ore": adjusted_rate,
        "base_hourly_rate_ore": hourly_rate_ore,
        "reason": reason + ".",
    }
