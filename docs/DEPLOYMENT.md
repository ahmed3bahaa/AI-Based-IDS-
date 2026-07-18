# Deployment Guide

These steps describe a clean Ubuntu lab deployment.

## 1. Clone And Prepare The Project

```bash
git clone https://github.com/ahmed3bahaa/AI-Based-IDS-.git
cd AI-Based-IDS-
python3 -m venv ids_venv
source ids_venv/bin/activate
pip install -r requirements.txt
```

## 2. Install System Dependencies

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch wireshark-common tshark \
  curl netcat-openbsd mosquitto-clients docker.io docker-compose-plugin
```

Install CICFlowMeter and confirm the CLI is available:

```bash
command -v cicflowmeter
```

If it is installed in a virtual environment or custom folder, set `CICFLOW` in `.env`.

## 3. Configure Environment

```bash
cp .env.example .env
nano .env
set -a
source .env
set +a
```

Set these values carefully:

- `ESP_IP`: ESP32 or target service IP address.
- `BROKER_IP`: MQTT broker IP address.
- `UPLINK`: Linux interface that reaches the LAN, for example `enp0s3`, `eth0`, or `wlan0`.
- `IFACE`: Mininet NAT interface, usually `nat0-eth0`.
- `CICFLOW`: path to the `cicflowmeter` executable if it is not on `PATH`.

## 4. Start PostgreSQL

```bash
docker compose up -d postgres
docker compose ps
```

The database listens on host port `5433`, and the alert table is created from `sql/init_ids_alerts.sql`.

## 5. Generate Live Traffic And CSV Features

```bash
bash run_live_detection.sh
```

This script:

1. starts Mininet attack traffic in the background
2. waits for the NAT capture interface
3. captures PCAPs with `dumpcap`
4. converts the PCAPs to CICFlowMeter CSV files
5. writes logs to `run_logs/<timestamp>/`

## 6. Start Spark Detection

In another terminal:

```bash
set -a
source .env
set +a

spark-submit --packages org.postgresql:postgresql:42.7.3 ids_streaming.py
```

Spark watches `CSV_DIR`, predicts attacks with `RF-20`, aggregates windows, and appends alerts to PostgreSQL.

## 7. Verify Alerts

```bash
docker compose exec postgres psql -U mluser -d mlanalytics \
  -c "SELECT id, window_start, src_ip, dst_ip, rule_attack_name, flow_count, pkt_count FROM ids_alerts ORDER BY id DESC LIMIT 20;"
```

## Troubleshooting

### `Interface nat0-eth0 did not appear`

Check Mininet logs in `run_logs/<timestamp>/mininet_attack.log`. Confirm `UPLINK` exists:

```bash
ip link
```

### `cicflowmeter not executable`

Set an absolute `CICFLOW` path in `.env`:

```bash
CICFLOW=/path/to/cicflowmeter
```

### Spark cannot connect to PostgreSQL

Confirm Docker is running and port `5433` is exposed:

```bash
docker compose ps
docker compose logs postgres
```

### No alerts are written

Confirm CSV files exist in `CSV_DIR`, the CSV destination IP matches `ESP_IP`, and thresholds are not too high for the generated traffic volume.

