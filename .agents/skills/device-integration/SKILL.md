---
name: device-integration
description: Connecting the marketplace to the device server. Use when handling occupancy or release events, checking presence for no-shows or ghost bookings, or changing DeviceAdapter.
---

# Device integration

The device API contract is in [device/README.md](../../../device/README.md); read it first. Marketplace-side setup (`MARKETPLACE_DEVICE_TOKEN`, the fixture adapter, `MARKETPLACE_DEVICE_ADAPTER`) is under "Connect a device" in [marketplace/README.md](../../../marketplace/README.md).

## Ownership

`device/` reports physical facts: whether a room is occupied, since when, and whether a staff member pressed **Release room**. It does not know about bookings. The marketplace owns bookings and decides on no-shows, overstays, auto-release, and pricing.

## Push: device server to marketplace

The device server posts `room.occupancy_changed` and `room.release_requested` to the existing `POST /internal/device/events`. Handle both types behind `DeviceAdapter` (`marketplace/backend/app/device.py`):

- Map a release request to the room's current block.
- An empty room during a booked block can be treated as a ghost-booking signal.

## Pull: marketplace to device server

The device server listens on port 8100.

- `GET /v1/rooms/{room_id}` returns current occupancy.
- `GET /v1/rooms/{room_id}/presence?from=&to=` reports whether anyone was in the room during a booking window. Check `coverage` before treating an empty window as a no-show.

## Room IDs

Room IDs are shared: the device server uses the marketplace's room IDs, such as `digs-demo-1`. Send timestamps as ISO 8601 with offsets.
