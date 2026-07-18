#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

PCAP_DIR="${PCAP_DIR:-/tmp/ids_live_pcaps}"
CSV_DIR="${CSV_DIR:-$SCRIPT_DIR/csv}"
CICFLOW="${CICFLOW:-$(command -v cicflowmeter || true)}"

mkdir -p "$CSV_DIR"

if [[ -z "$CICFLOW" || ! -x "$CICFLOW" ]]; then
  echo "[pcap_to_csv] ERROR: cicflowmeter not found or not executable:"
  echo "  ${CICFLOW:-<empty>}"
  echo "Set CICFLOW=/path/to/cicflowmeter or install it on PATH."
  exit 1
fi

echo "[pcap_to_csv] Processing PCAP_DIR=$PCAP_DIR"
echo "[pcap_to_csv] Writing CSV_DIR=$CSV_DIR"
echo "[pcap_to_csv] Using CICFLOW=$CICFLOW"

shopt -s nullglob
pcaps=("$PCAP_DIR"/*.pcap)
shopt -u nullglob

if [[ "${#pcaps[@]}" -eq 0 ]]; then
  echo "[pcap_to_csv] ERROR: No PCAP files found in $PCAP_DIR"
  exit 1
fi

LATEST_PCAP="$(ls -t "${pcaps[@]}" | head -n 1)"
base="$(basename "$LATEST_PCAP" .pcap)"
out="$CSV_DIR/${base}.csv"

# Skip if already converted
if [[ -s "$out" ]]; then
  echo "[pcap_to_csv] CSV already exists for $LATEST_PCAP. Skipping conversion."
  exit 0
fi


echo "[pcap_to_csv] Converting $LATEST_PCAP -> $out"
"$CICFLOW" -f "$LATEST_PCAP" -c "$out" || {
  echo "[pcap_to_csv] WARNING: cicflowmeter failed for $LATEST_PCAP"
  rm -f "$out"
  exit 1
}

# Check if conversion was successful (CSV file is not empty)
if [[ ! -s "$out" ]]; then
  echo "[pcap_to_csv] Empty CSV. Removing $out"
  rm -f "$out"
  exit 1
fi

echo "[pcap_to_csv] Conversion completed successfully."
