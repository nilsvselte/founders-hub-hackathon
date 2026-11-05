#!/bin/sh
# Renders the PNG app icons from app/icon.svg with headless Chrome.
# Run from marketplace/frontend/: sh scripts/make-icons.sh
set -eu
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
bg="#0A0E18"
work="$(mktemp -d)"
svg="$(sed 's/ width="512" height="512"//' app/icon.svg)"

render() { # output size scale
  cat > "$work/page.html" <<HTML
<!doctype html><html><head><style>html,body{margin:0;background:$bg;overflow:hidden}
div{width:$2px;height:$2px;display:flex;align-items:center;justify-content:center}
svg{width:calc($2px * $3);height:calc($2px * $3);display:block}</style></head>
<body><div>$svg</div></body></html>
HTML
  "$chrome" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --screenshot="$PWD/$1" --window-size="$2,$2" "file://$work/page.html" 2>/dev/null
}

render public/icons/icon-192.png 192 1
render public/icons/icon-512.png 512 1
# Maskable: art scaled to 80% so it stays inside the safe zone.
render public/icons/icon-maskable-512.png 512 0.8
render app/apple-icon.png 180 1
rm -rf "$work"
