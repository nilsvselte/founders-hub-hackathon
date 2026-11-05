// Copy to secrets.h (gitignored) and fill in. WiFi must be 2.4 GHz
// (iPhone hotspot: turn on Maximize Compatibility).
#define WIFI_SSID "Afras iPhone"
#define WIFI_PASS "change-me"
// The device server's address on that network (Mac on iPhone hotspot: 172.20.10.x).
#define SERVER_URL "http://172.20.10.3:8100/v1/telemetry"
#define DEVICE_ID "dev-1"
// Must match DEVICE_TOKEN in device/server/.env. Leave empty if that is empty.
#define DEVICE_TOKEN ""
