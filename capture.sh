#!/usr/bin/env bash
set -euo pipefail

ESP_IP="${ESP_IP:-192.168.151.40}"
BROKER_IP="${BROKER_IP:-}"                 # optional
IFACE="${IFACE:-nat0-eth0}"
OUTDIR="${OUTDIR:-/tmp/ids_live_pcaps}"    # use /tmp to avoid sudo/home permission drama
DUR="${DUR:-10}"
KEEP="${KEEP:-120}"

mkdir -p "$OUTDIR"

echo "[capture] waiting for interface: $IFACE ..."
for _ in $(seq 1 50); do
  if ip link show "$IFACE" &>/dev/null; then break; fi
  sleep 0.1
done
ip link show "$IFACE" >/dev/null

# filter
if [[ -n "$BROKER_IP" ]]; then
  FILTER="(host $ESP_IP or host $BROKER_IP) and (tcp or udp)"
else
  FILTER="host $ESP_IP and (tcp or udp)"
fi

echo "[capture] Capturing on '$IFACE' -> $OUTDIR (chunk ${DUR}s, keep ${KEEP})"
echo "[capture] Filter: $FILTER"

exec dumpcap -q \
  -i "$IFACE" \
  -f "$FILTER" \
  -b "duration:$DUR" -b "files:$KEEP" \
  -P \
  -w "$OUTDIR/esp32.pcap"

