#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"

ESP_IP="${ESP_IP:-192.168.151.210}"
BROKER_IP="${BROKER_IP:-192.168.150.137}"
TCP_PORT="${TCP_PORT:-9000}"

UPLINK="${UPLINK:-enp0s3}"                 
CONTROLLER_IP="${CONTROLLER_IP:-}"        


IFACE="${IFACE:-nat0-eth0}"
PCAP_DIR="${PCAP_DIR:-/tmp/ids_live_pcaps}"
CSV_DIR="${CSV_DIR:-$PROJECT_DIR/csv}"


ATTACK_SECS="${ATTACK_SECS:-180}"          
WARMUP="${WARMUP:-10}"
PARALLEL="${PARALLEL:-10}"


HTTP_RPS="${HTTP_RPS:-20}"
TCP_RPS="${TCP_RPS:-20}"
MQTT_RPS="${MQTT_RPS:-40}"


HTTP_N="${HTTP_N:-$((HTTP_RPS * ATTACK_SECS))}"
TCP_N="${TCP_N:-$((TCP_RPS  * ATTACK_SECS))}"
MQTT_N="${MQTT_N:-$((MQTT_RPS * ATTACK_SECS))}"


CICFLOW="${CICFLOW:-$(command -v cicflowmeter || true)}"


LOG_DIR="${LOG_DIR:-$PROJECT_DIR/run_logs/$(date +%Y%m%d_%H%M%S)}"


SPARK_APP="${SPARK_APP:-$PROJECT_DIR/ids_streaming.py}"
SPARK_PACKAGES="${SPARK_PACKAGES:-org.postgresql:postgresql:42.7.3}"

# -----------------------------------------
# Helpers
# -----------------------------------------
need() { [[ -e "$1" ]] || { echo "Missing: $1" >&2; exit 1; }; }
die()  { echo "ERROR: $*" >&2; exit 1; }

mkdir -p "$LOG_DIR" "$PCAP_DIR" "$CSV_DIR"

need "$PROJECT_DIR/capture.sh"
need "$PROJECT_DIR/mininet_attack.py"
need "$SPARK_APP"

[[ -n "$CICFLOW" && -x "$CICFLOW" ]] || die "cicflowmeter not found or not executable. Set CICFLOW=/path/to/cicflowmeter"

echo "[*] Logs: $LOG_DIR"
echo "[*] ESP_IP=$ESP_IP  IFACE=$IFACE  UPLINK=$UPLINK"
echo "[*] PCAP_DIR=$PCAP_DIR"
echo "[*] CSV_DIR=$CSV_DIR"
echo "[*] Attack ~${ATTACK_SECS}s  (HTTP_N=$HTTP_N, TCP_N=$TCP_N, MQTT_N=$MQTT_N, PARALLEL=$PARALLEL)"


sudo -v


if [[ "${CLEAN_PREV:-1}" == "1" ]]; then
  rm -f "$PCAP_DIR"/*.pcap 2>/dev/null || true
  rm -f "$CSV_DIR"/*.csv   2>/dev/null || true
fi

MININET_PID=""
CAPTURE_PID=""

cleanup() {
  set +e
  if [[ -n "${CAPTURE_PID}" ]] && ps -p "$CAPTURE_PID" >/dev/null 2>&1; then
    echo "[cleanup] stopping capture (pid=$CAPTURE_PID)"
    sudo kill -INT "$CAPTURE_PID" 2>/dev/null || true
    sleep 1
    sudo kill -KILL "$CAPTURE_PID" 2>/dev/null || true
  fi
  if [[ -n "${MININET_PID}" ]] && ps -p "$MININET_PID" >/dev/null 2>&1; then
    echo "[cleanup] stopping mininet (pid=$MININET_PID)"
    sudo kill -INT "$MININET_PID" 2>/dev/null || true
    sleep 1
    sudo kill -KILL "$MININET_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT


echo "[1/4] Start Mininet traffic (background)..."
sudo -E python3 "$PROJECT_DIR/mininet_attack.py" \
  --esp "$ESP_IP" \
  --broker "$BROKER_IP" \
  --tcp-port "$TCP_PORT" \
  --http-n "$HTTP_N" --tcp-n "$TCP_N" --mqtt-n "$MQTT_N" \
  --warmup "$WARMUP" \
  --parallel "$PARALLEL" \
  ${CONTROLLER_IP:+--controller-ip "$CONTROLLER_IP"} \
  --uplink "$UPLINK" \
  >"$LOG_DIR/mininet_attack.log" 2>&1 &
MININET_PID=$!
echo "    mininet pid: $MININET_PID"
echo "    (watch) tail -f $LOG_DIR/mininet_attack.log"


echo "[2/4] Wait for capture interface ($IFACE) to exist..."
for i in {1..30}; do
  if ip link show "$IFACE" >/dev/null 2>&1; then
    echo "    Interface $IFACE is up."
    break
  fi
  sleep 1
done
ip link show "$IFACE" >/dev/null 2>&1 || die "Interface $IFACE did not appear. Check $LOG_DIR/mininet_attack.log"

echo "[2/4] Start capture..."
sudo -E env ESP_IP="$ESP_IP" BROKER_IP="$BROKER_IP" IFACE="$IFACE" PCAP_DIR="$PCAP_DIR" \
  bash "$PROJECT_DIR/capture.sh" \
  >"$LOG_DIR/capture.log" 2>&1 &
CAPTURE_PID=$!
echo "    capture pid: $CAPTURE_PID"
echo "    (watch) tail -f $LOG_DIR/capture.log"


echo "[3/4] Waiting for Mininet to finish..."
wait "$MININET_PID" || true
MININET_PID=""

echo "[3/4] Stop capture..."
sudo kill -INT "$CAPTURE_PID" 2>/dev/null || true
for _ in {1..10}; do
  if ps -p "$CAPTURE_PID" >/dev/null 2>&1; then sleep 1; else break; fi
done
if ps -p "$CAPTURE_PID" >/dev/null 2>&1; then
  sudo kill -KILL "$CAPTURE_PID" 2>/dev/null || true
fi
CAPTURE_PID=""


echo "[4/4] Convert PCAP(s) -> CSV(s)..."
mapfile -t PCAPS < <(ls -1 "$PCAP_DIR"/*.pcap 2>/dev/null | sort || true)
[[ "${#PCAPS[@]}" -gt 0 ]] || die "No PCAPs found in $PCAP_DIR. Check $LOG_DIR/capture.log"

ok=0
for pcap in "${PCAPS[@]}"; do
  base="$(basename "$pcap" .pcap)"
  out="$CSV_DIR/${base}.csv"

  
  sudo chown "$USER:$USER" "$pcap" 2>/dev/null || true
  sudo chmod a+r "$pcap" 2>/dev/null || true

  echo "    Converting: $pcap -> $out"
  "$CICFLOW" -f "$pcap" -c "$out" >>"$LOG_DIR/cicflowmeter.log" 2>&1 || {
    echo "    WARNING: cicflowmeter failed for $pcap (see $LOG_DIR/cicflowmeter.log)"
    rm -f "$out" 2>/dev/null || true
    continue
  }

  if [[ ! -s "$out" ]]; then
    echo "    WARNING: empty CSV produced, removing: $out"
    rm -f "$out" 2>/dev/null || true
    continue
  fi

  rows=$(( $(wc -l < "$out") - 1 ))
  echo "    OK: $out  rows=$rows"
  ok=$((ok+1))
done

echo "[*] Conversion complete. CSV files ready in: $CSV_DIR  (ok=$ok)"

echo
echo "[NEXT] Run Spark manually when you want:"
echo "  export ESP_IP=\"$ESP_IP\""
echo "  export CSV_DIR=\"$CSV_DIR\""
echo "  spark-submit --packages \"$SPARK_PACKAGES\" \"$SPARK_APP\""
