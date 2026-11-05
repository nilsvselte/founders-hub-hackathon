# Notifications

standbyroom sends web push notifications to hosts and bookers on the devices where they switched push on. Each kind of notification is on by default, and each person can switch each kind off. The browser side (service worker, subscribing a device) is in [phone-app.md](phone-app.md); this page covers the backend and the settings.

## Who gets what

| Kind | Who | When | Opens |
| --- | --- | --- | --- |
| `offer_ready` | Booker | A room freed up for their standby request and an offer was made. With automatic booking it says the room is booked. | `/bookings/<request id>` |
| `room_booked` | Host | One of their rooms got a confirmed booking (offer accepted, or booked automatically). | `/host` |
| `occupied_unbooked` | Host | The sensor reports people in their room, and no confirmed booking or scheduled block covers now. At most once per room per 30 minutes. | `/host` |
| `booked_empty` | Host | A confirmed booking started more than 10 minutes ago, and the room's latest sensor state is empty or there is no reading. Once per booking. | `/host` |

Only rooms with an owner (host-created listings) send host notifications; catalog rooms have no host account. Texts are short and in English.

## The module

Everything lives in [`marketplace/backend/app/notify.py`](../marketplace/backend/app/notify.py). The rest of the backend uses one call:

```python
notify(user_id, kind, title, body, url)
```

It returns at once. In a background thread it checks the user's settings, sends the payload `{kind, title, body, url}` to every subscription of that user with `pywebpush`, deletes subscriptions the push service answers with 404 or 410, and logs any other error. It never raises into the caller.

The event helpers in the same file find the right person and text, then call `notify`. They also run in the background thread:

- `offer_created(offer_id)`: tells the booker (`offer_ready`), and the host (`room_booked`) when the offer was booked automatically.
- `booking_confirmed(offer_id)`: tells the host (`room_booked`).
- `occupancy_changed(room_id)`: tells the host (`occupied_unbooked`) if the room is occupied and unbooked.
- `watch_booked_empty()`: an asyncio loop started when the app starts. Every 60 seconds it runs `check_booked_empty()`, which tells hosts about empty booked rooms (`booked_empty`).

Repeats are blocked through `marketplace_notification_log`, keyed like `room_booked:<offer id>` or `occupied_unbooked:<room id>`. A retried webhook or a re-accepted offer does not send twice.

## Where the triggers are

All in [`marketplace/backend/app/main.py`](../marketplace/backend/app/main.py):

| Event | Place | Call |
| --- | --- | --- |
| Standby match made an offer (manual or automatic booking) | `_match_candidates`, after `db.create_offer` | `notify.offer_created` |
| Booker accepted an offer | `accept_standby_offer`, after `db.accept_offer` | `notify.booking_confirmed` |
| Sensor reported a room occupied | `device_event`, after `db.record_occupancy` recorded a new state | `notify.occupancy_changed` |
| Booked room still empty | `start_notification_watch` on app startup | `notify.watch_booked_empty` |

## Settings

Settings are per account, stored in `marketplace_notification_settings` (one boolean per kind; a missing row means everything on). Each account has one role, so the UI shows hosts `room_booked`, `occupied_unbooked` and `booked_empty`, and renters `offer_ready`.

The settings page is `/account/notifications` in [`marketplace/frontend`](../marketplace/frontend/app/account/notifications). Its device on/off button uses [`app/push-client.ts`](../marketplace/frontend/app/push-client.ts); its switches call `GET` and `PUT /notifications/settings` and save on tap.

## API

All endpoints need a signed-in user. Writes also need the `X-Marketplace-Request: 1` header, like every browser mutation.

| Endpoint | Body | Returns |
| --- | --- | --- |
| `GET /push/public-key` | | `{"publicKey": "<base64url VAPID public key>"}`, or 503 when keys are not set |
| `POST /push/subscriptions` | `{endpoint, keys: {p256dh, auth}}` (a browser `PushSubscription.toJSON()`) | 204. Upsert by endpoint |
| `DELETE /push/subscriptions` | `{endpoint}` | 204. Only removes the caller's own device |
| `GET /notifications/settings` | | `{"room_booked": true, "occupied_unbooked": true, "booked_empty": true, "offer_ready": true}` |
| `PUT /notifications/settings` | Any subset of those four booleans | The full settings |

Tables: [`020_push_notifications.sql`](../marketplace/backend/app/migrations/020_push_notifications.sql).

## VAPID keys

Push services need a VAPID key pair. The backend reads:

- `VAPID_PUBLIC_KEY`: base64url uncompressed P-256 public key (what the browser subscribes with).
- `VAPID_PRIVATE_KEY`: base64url raw 32-byte private key.
- `VAPID_SUBJECT`: a contact, `mailto:hello@standbyroom.com` by default.

Without the two keys the app still starts; `notify` logs once and sends nothing, and `GET /push/public-key` returns 503. Keys go in a gitignored `.env`, never in the repo: `marketplace/.env` for Docker Compose (passed through in [`compose.yaml`](../marketplace/compose.yaml)), `marketplace/backend/.env` for `uv run`. On Render they are secret env vars in [`render.preview.yaml`](../marketplace/render.preview.yaml).

Generate a pair from `marketplace/backend/`:

```sh
uv run --locked python -c "
import base64; from cryptography.hazmat.primitives.asymmetric import ec; from cryptography.hazmat.primitives import serialization as s
k = ec.generate_private_key(ec.SECP256R1()); b = lambda x: base64.urlsafe_b64encode(x).rstrip(b'=').decode()
print('VAPID_PUBLIC_KEY=' + b(k.public_key().public_bytes(s.Encoding.X962, s.PublicFormat.UncompressedPoint)))
print('VAPID_PRIVATE_KEY=' + b(k.private_numbers().private_value.to_bytes(32, 'big')))"
```

Changing the keys invalidates every existing subscription; devices must switch push on again.

## Test a push locally

1. Put the keys in the `.env` and start the stack (see [marketplace/README.md](../marketplace/README.md)). Push needs HTTPS outside localhost; [phone-app.md](phone-app.md) shows the tunnel for a phone.
2. Sign in, open `/account/notifications`, and switch push on for this device.
3. Send yourself one from `marketplace/backend/` (same `DATABASE_URL` and VAPID env as the API):

   ```sh
   uv run --locked --env-file .env python -c "
   from app import notify, db
   uid = db._connect().execute(\"SELECT id FROM marketplace_users WHERE email = 'you@example.com'\").fetchone()['id']
   notify._deliver(str(uid), 'room_booked', 'Test push', 'It works.', '/host')"
   ```

   `_deliver` is the synchronous inside of `notify`, so errors print here.
4. Or trigger a real one: as a renter, request a host's room and press **Release demo room** (`offer_ready` to the renter); accept the offer (`room_booked` to the host).

Backend tests: `tests/test_notify.py` (settings, subscriptions, switched-off kinds, dedupe). Run them as in [marketplace/README.md](../marketplace/README.md#run-backend-checks).
