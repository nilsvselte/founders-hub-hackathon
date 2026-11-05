# Phone app

The marketplace is a web app you can add to a phone's home screen. It then opens full screen with the standbyroom icon and can receive push notifications. There is no app-store build.

## What makes it installable

| Piece | File |
| --- | --- |
| Web app manifest (name, colours, icons, `display: standalone`) | [`app/manifest.ts`](../marketplace/frontend/app/manifest.ts), served at `/manifest.webmanifest` |
| Theme colour and iOS home-screen tags | `viewport` and `metadata.appleWebApp` in [`app/layout.tsx`](../marketplace/frontend/app/layout.tsx) |
| Service worker registration | [`app/sw-register.tsx`](../marketplace/frontend/app/sw-register.tsx), mounted in the layout |
| Service worker | [`public/sw.js`](../marketplace/frontend/public/sw.js) |

Theme and background colour are `#0A0E18`, the logo's background.

## Icons

The "lit window" logo is [`app/icon.svg`](../marketplace/frontend/app/icon.svg); Next.js serves it as the favicon. The PNGs are rendered from it:

- `public/icons/icon-192.png`, `public/icons/icon-512.png`: manifest icons.
- `public/icons/icon-maskable-512.png`: the art scaled to 80% on the logo background, so Android's round or squircle masks don't clip it.
- `app/apple-icon.png` (180×180): the iOS home-screen icon.

To regenerate after changing `icon.svg`, run `sh scripts/make-icons.sh` from `marketplace/frontend/`. It uses headless Google Chrome; set `CHROME` to another Chrome binary if needed. The script expects the SVG's `viewBox` to be `0 0 512 512`.

## Service worker

`public/sw.js` does three things and caches nothing:

- Passes every request to the network (a fetch handler is part of what makes browsers offer install).
- On `push`, reads the JSON payload `{title, body, url, tag?}` and shows a notification. The same `tag` replaces an earlier notification.
- On a notification tap, focuses a window already on `url`, else navigates an open standbyroom window there, else opens a new one.

## Push from the page

[`app/push-client.ts`](../marketplace/frontend/app/push-client.ts) is the only module the UI uses:

- `getPushState()` → `"unsupported" | "needs-install" | "denied" | "off" | "on"`. `needs-install` means iOS Safari that is not running from the home screen.
- `enablePush()` → `"on" | "denied" | "unsupported" | "needs-install"`. Call it from a tap: it asks permission, fetches the VAPID key from `GET /push/public-key`, subscribes, and sends the subscription to `POST /push/subscriptions`. It throws `ApiError` if the server refuses (for example, signed out).
- `disablePush()` unsubscribes this device and calls `DELETE /push/subscriptions` with `{endpoint}`.

Calls go through `/api/*` with the app's usual `X-Marketplace-Request` header, like every other browser call. All push endpoints need a signed-in user.

## iOS

Push works on iOS 16.4 and later, and only after the user adds the site to the home screen (Share → Add to Home Screen) and opens it from there. In Safari, `getPushState()` returns `needs-install`.

## Open it on a phone

Service workers and push need HTTPS (localhost is the only exception). With the app on port 3000, start a free Cloudflare quick tunnel:

```sh
cloudflared tunnel --url http://localhost:3000
```

Open the printed `https://….trycloudflare.com` URL on the phone. The URL changes every run, so a home-screen install and its push subscription only last as long as that tunnel; reinstall after restarting it.
