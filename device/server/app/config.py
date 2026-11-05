"""Settings read from the environment. See .env.example for every variable."""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


def _devices(raw: str) -> dict[str, str]:
    devices: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        device_id, sep, room_id = item.partition(":")
        if not sep or not device_id.strip() or not room_id.strip():
            raise RuntimeError(f"DEVICES entry {item!r} must look like device_id:room_id")
        devices[device_id.strip()] = room_id.strip()
    return devices


@dataclass(frozen=True)
class Settings:
    devices: dict[str, str]
    device_token: str
    marketplace_url: str
    marketplace_token: str
    database_path: str
    presence_delta_mm: int
    presence_near_mm: int
    presence_min_zones: int
    occupied_after_frames: int
    empty_after_seconds: float
    offline_after_seconds: float
    timezone: ZoneInfo

    @property
    def rooms(self) -> list[str]:
        return sorted(set(self.devices.values()))

    def devices_in(self, room_id: str) -> list[str]:
        return sorted(d for d, r in self.devices.items() if r == room_id)


def load_settings() -> Settings:
    env = os.environ.get
    return Settings(
        devices=_devices(env("DEVICES", "dev-1:digs-demo-1")),
        device_token=env("DEVICE_TOKEN", "").strip(),
        marketplace_url=env("MARKETPLACE_URL", "").strip().rstrip("/"),
        marketplace_token=env("MARKETPLACE_DEVICE_TOKEN", "").strip(),
        database_path=env("DATABASE_PATH", "device.db"),
        presence_delta_mm=int(env("PRESENCE_DELTA_MM", "250")),
        presence_near_mm=int(env("PRESENCE_NEAR_MM", "1200")),
        presence_min_zones=int(env("PRESENCE_MIN_ZONES", "3")),
        occupied_after_frames=int(env("OCCUPIED_AFTER_FRAMES", "2")),
        empty_after_seconds=float(env("EMPTY_AFTER_SECONDS", "30")),
        offline_after_seconds=float(env("OFFLINE_AFTER_SECONDS", "30")),
        timezone=ZoneInfo(env("TIMEZONE", "Europe/Oslo")),
    )
