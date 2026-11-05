# TP discovery and verification — 5 November 2026

## Correction to initial research

There **is public API documentation**, including room availability, booking and
cancellation: [Swagger UI](https://tp.educloud.no/ntnu/ws/swagger-ui/dist/) and
[OpenAPI JSON](https://tp.educloud.no/ntnu/ws/openapi.json). Both returned HTTP 200
when fetched directly. Earlier web-fetch tool 403 responses did not establish
that documentation was unavailable.

The OpenAPI file reports `openapi: 3.0.1`, title `TP-API`, API version `1.4`.
Its room-booking operations include:

- `GET /ws/roombooking/possible.php` with start/end and optional user/location fields.
- `POST /ws/roombooking/reservation.php` with userid/dtstart/dtend/roomid/name.
- `DELETE /ws/roombooking/reservation.php` with bookingid/userid.

These operations reference `ApiKeyAuth`. The fetched specification does not
include a `components.securitySchemes` definition, so its API-key header and
provisioning procedure are **not established** by that file. Those API-key
operations were not invoked. This experiment uses the current web app's session
interface instead. These are two different observed contracts.

## Current web app contract

The public [booking app](https://tp.educloud.no/ntnu/app/rombestilling/) returned
HTTP 200 and referenced
[`/app/assets/index-BuQMiyWi.js`](https://tp.educloud.no/app/assets/index-BuQMiyWi.js).
That source contains the paths, methods and field names below. Its Axios request
interceptor prefixes institution-scoped paths with `/ntnu`.

| Method and path (under `/ntnu`) | Observed behavior |
| --- | --- |
| `GET /ws/user/session.php` | Logged-in user is identified by `username`; unauthenticated probe returned HTTP 200 with an empty body |
| `GET /ws/room/2.0/areas.php` | Public probe returned a `data` array with 16 areas |
| `GET /ws/room/2.0/buildings.php` | Public probe returned a `data` array with 102 buildings |
| `GET /ws/rombestilling/possible.php` | Query `start`, `end`, optional repeated `roomid[]`; unauthenticated probe returned HTTP 401, `Access denied` |
| `GET /ws/rombestilling/bookings.php` | Current user's bookings; unauthenticated probe returned HTTP 401 |
| `GET /ws/user/quotas.php` | Current quota information; unauthenticated probe returned HTTP 200 with an empty body |
| `POST /ws/rombestilling/reservation.php` | Current frontend sends JSON shown below; **no live POST made** |
| `DELETE /ws/rombestilling/reservation.php?id=...` | Frontend checks `deleted`; **no live DELETE made** |

Single room reservation JSON from the app source:

```json
{
  "rooms": ["room-id-from-search"],
  "userGroup": null,
  "name": "Booking name",
  "notes": "",
  "start": "2026-11-06T12:00:00",
  "end": "2026-11-06T13:00:00"
}
```

The app checks `reservations-completed`, an array of results with `ok` and `id`.
It uses `available`, `can_book` and `size` to decide whether a room is directly
bookable. The adapter follows this behavior and excludes individual seat bookings.
It does not submit API-key API fields to the session interface.

Login is initiated at `/ntnu/login/?redirect=...`. The app uses session cookies;
Axios includes its default `XSRF-TOKEN`/`X-XSRF-TOKEN` handling. No custom CSRF
interceptor was found in the inspected bundle. Whether authenticated TP currently
sets that cookie remains unverified.

## Existing code

Historical examples establish that TP has been automated before, but target the
older `tp.uio.no/ntnu/rombestilling/` UI:

- [Iskers/Rombooking](https://github.com/Iskers/Rombooking/blob/main/requests_driver.py): HTTP session, SAML and form POSTs.
- [skulstadv/NTNU-Roomshark](https://github.com/skulstadv/NTNU-Roomshark): Python/Selenium.
- [allkjeks/Romrez](https://github.com/allkjeks/Romrez): Python/Selenium.
- [EwanMe/romresbot](https://github.com/EwanMe/romresbot): Java/Selenium and scheduling.

None was used as proof of compatibility with today's app. This experiment's live
payloads come from the current first-party JavaScript.

## Verified and unverified

Verified locally: MCP initialization/tool discovery and the entire synthetic
search → book → list → overlap rejection → cancel → availability restored flow.
Public TP locations and unauthenticated access behavior verified using the
implemented HTTP adapter. Lint and tests are recorded in `validation.md`.

Remaining: interactive Feide login, authenticated availability/quota response
shapes, real single-room creation and cancellation, session longevity/rotation,
and TP's exact authenticated error behavior. No real rooms have been booked.

API-key access can be investigated through the institution's TP administrator;
[TP's contact guidance](https://tp-info.educloud.no/om/kontakt/) directs
institutional questions through that administrator. The public specification alone
does not establish that a student can obtain an API key.
