#!/bin/sh
# Systemnivaa for marketplace + device paa rpi5. Krever sudo.
#   ssh -t rpi5 "sudo sh ~/deploy/standbyroom-apps/install-system.sh"
# Idempotent. Tar backup av cloudflared-configen og ruller tilbake ved feil.
set -eu
CF=/etc/cloudflared/config.yml

echo "==> PostgreSQL"
if ! command -v psql >/dev/null 2>&1; then
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql >/dev/null
fi
systemctl enable --now postgresql >/dev/null 2>&1 || true
su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='marketplace'\"" | grep -q 1 || \
	su postgres -c "psql -qc \"CREATE ROLE marketplace LOGIN PASSWORD 'marketplace'\""
su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='marketplace'\"" | grep -q 1 || \
	su postgres -c "createdb -O marketplace marketplace"
echo "    postgres klar"

echo "==> Cloudflared ingress"
SIKKER="$CF.bak.$(date +%Y%m%d%H%M%S)"
cp -p "$CF" "$SIKKER"
for PAR in device.standbyroom.com:8012 api.standbyroom.com:8013 app.standbyroom.com:8014; do
	if ! python3 /home/afras/deploy/standbyroom/cf_ingress.py "$CF" "${PAR%%:*}" "${PAR##*:}"; then
		cp -p "$SIKKER" "$CF"; echo "    !! rullet tilbake"; exit 1
	fi
done
if cloudflared --config "$CF" tunnel ingress validate; then
	cmp -s "$SIKKER" "$CF" && rm "$SIKKER" || { systemctl restart cloudflared.service; echo "    cloudflared restartet"; }
else
	cp -p "$SIKKER" "$CF"; echo "    !! ingress ugyldig - rullet tilbake"; exit 1
fi
echo "Ferdig."
