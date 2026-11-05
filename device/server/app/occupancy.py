"""Turn raw ToF frames into room occupancy.

A frame is "present" when enough ToF zones are closer than the empty-room
baseline (or, before calibration, closer than an absolute distance). A room
turns occupied after a few present frames in a row, and turns empty after a
quiet period with no present frame. The board stays dumb: every threshold
lives here so it can change without a reflash.
"""

from collections.abc import Sequence

from .config import Settings

TOF_ZONES = 64
# The VL53L5CX ranges to about 4 m and reports a large sentinel when a zone sees nothing.
MAX_RANGE_MM = 4000


def valid_frame(tof_mm: Sequence[object] | None) -> list[int | None] | None:
    """Return 64 distances (None for an unusable zone), or None for a missing frame."""
    if tof_mm is None:
        return None
    if len(tof_mm) != TOF_ZONES:
        raise ValueError(f"tof_mm must have {TOF_ZONES} values")
    zones: list[int | None] = []
    for value in tof_mm:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < MAX_RANGE_MM:
            zones.append(None)  # no valid target in this zone
        else:
            zones.append(int(value))
    return zones


def frame_present(
    frame: Sequence[int | None], baseline: Sequence[int | None] | None, settings: Settings
) -> bool:
    """True when enough zones look like a person."""
    hits = 0
    for i, distance in enumerate(frame):
        if distance is None:
            continue
        reference = baseline[i] if baseline is not None else None
        if reference is not None:
            if reference - distance >= settings.presence_delta_mm:
                hits += 1
        elif distance <= settings.presence_near_mm:
            hits += 1
    return hits >= settings.presence_min_zones
