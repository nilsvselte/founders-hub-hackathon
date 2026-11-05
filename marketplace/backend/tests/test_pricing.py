from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from app.pricing import quote_price


class RoomPricingTests(unittest.TestCase):
    def quote(
        self,
        start_at: datetime,
        *,
        now: datetime = datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
        duration_minutes: int = 60,
        minimum_hourly_rate_ore: int = 30_000,
        maximum_hourly_rate_ore: int = 50_000,
    ):
        return quote_price(
            hourly_rate_ore=40_000,
            minimum_hourly_rate_ore=minimum_hourly_rate_ore,
            maximum_hourly_rate_ore=maximum_hourly_rate_ore,
            start_at=start_at,
            duration_minutes=duration_minutes,
            now=now,
        )

    def test_same_room_costs_less_in_the_evening_and_on_the_weekend(self):
        cases = (
            ("2026-07-06T11:00:00+02:00", 48_000, "Weekday peak"),
            ("2026-07-06T18:00:00+02:00", 34_000, "Weekday off-peak"),
            ("2026-07-11T11:00:00+02:00", 32_000, "Weekend"),
        )
        for timestamp, expected_price, reason in cases:
            with self.subTest(timestamp=timestamp):
                quote = self.quote(datetime.fromisoformat(timestamp))
                self.assertEqual(quote["price_ore"], expected_price)
                self.assertIn(reason, quote["reason"])

    def test_peak_start_follows_oslo_clock_in_winter_and_summer(self):
        oslo = ZoneInfo("Europe/Oslo")
        cases = (
            (datetime(2026, 1, 5, 9, tzinfo=oslo), "2026-01-05T08:00:00+00:00"),
            (datetime(2026, 7, 6, 9, tzinfo=oslo), "2026-07-06T07:00:00+00:00"),
        )
        for local_start, utc_timestamp in cases:
            with self.subTest(local_start=local_start):
                local_quote = self.quote(local_start)
                self.assertEqual(local_quote["price_ore"], 48_000)
                self.assertEqual(local_quote, self.quote(datetime.fromisoformat(utc_timestamp)))

    def test_room_bounds_apply_before_rounding_partial_hour_quotes(self):
        peak = self.quote(
            datetime.fromisoformat("2026-07-06T11:00:00+02:00"),
            duration_minutes=45,
            maximum_hourly_rate_ore=45_001,
        )
        self.assertEqual((peak["hourly_rate_ore"], peak["price_ore"]), (45_001, 33_751))
        self.assertIn("Room maximum applied", peak["reason"])

        last_minute = self.quote(
            datetime.fromisoformat("2026-07-06T18:00:00+02:00"),
            now=datetime.fromisoformat("2026-07-06T17:45:00+02:00"),
            duration_minutes=45,
            minimum_hourly_rate_ore=33_001,
        )
        self.assertEqual((last_minute["hourly_rate_ore"], last_minute["price_ore"]), (33_001, 24_751))
        self.assertIn("Last-minute discount", last_minute["reason"])
        self.assertIn("Room minimum applied", last_minute["reason"])
