# AI-Based Intrusion Detection System for IoT Traffic

An end-to-end intrusion detection pipeline that simulates attacks against an ESP32/IoT target, captures live packets, extracts CICFlowMeter-style flow features, classifies traffic with a trained Spark ML Random Forest model, and stores actionable alerts in PostgreSQL.

The project is designed for a Linux/Ubuntu lab environment with Mininet and an ESP32 or reachable test service on the LAN. It is useful for demonstrating AI-assisted network monitoring, IoT attack simulation, and real-time alert generation.

## What This Project Does

- Builds a Mininet topology with three attack hosts and a NAT uplink to the physical LAN.
- Generates HTTP, TCP, and MQTT traffic toward an ESP32 target and MQTT broker.
- Captures traffic with `dumpcap` on the Mininet NAT interface.
- Converts PCAP chunks to CIC-style CSV flow records with CICFlowMeter.
- Streams new CSV files into Apache Spark Structured Streaming.
- Loads the saved `RF-20` Spark ML pipeline model.
- Maps model predictions to attack names such as `DoS_Hulk`, `PortScan`, `DDoS`, `Bot`, web attacks, and `Heartbleed`.
- Applies a 10-second rule aggregation layer to reduce noisy per-flow predictions into alert windows.
- Writes non-benign alerts to PostgreSQL for dashboards, analysis, or reporting.

## Repository Structure

```text
.
├── RF-20/                    # Saved Spark ML pipeline model
├── capture.sh                # Live packet capture using dumpcap
├── cic_schema.json           # Spark schema for CICFlowMeter CSV files
├── docker-compose.yml        # Local PostgreSQL deployment for IDS alerts
├── gen_schema.py             # Helper to regenerate cic_schema.json from sample CSV
├── ids_streaming.py          # Spark Structured Streaming IDS engine
├── mininet_attack.py         # Mininet attack traffic generator
├── pcap_to_csv.sh            # Convert latest PCAP to CSV with CICFlowMeter
├── run_live_detection.sh     # Orchestrates attack, capture, and conversion
├── sql/init_ids_alerts.sql   # PostgreSQL alert table schema
└── docs/                     # Architecture, deployment, and GitHub publishing notes
```

Generated folders such as `csv/`, `pcaps/`, `logs/`, `run_logs/`, and `checkpoints/` are intentionally ignored by Git.

## System Requirements

Use Ubuntu or another Linux environment that supports Mininet. Packet capture and Mininet setup require `sudo`.

Core tools:

- Python 3.10+
- Java 8, 11, or 17 supported by your Spark installation
- Apache Spark 3.5+
- Mininet
- Open vSwitch
- Wireshark CLI tools, especially `dumpcap`
- CICFlowMeter CLI
- PostgreSQL, or Docker Compose for the included database setup
- MQTT client tools such as `mosquitto-clients`
- `curl` and `netcat`

Example Ubuntu packages:

```bash
sudo apt update
sudo apt install -y python3 python3-pip mininet openvswitch-switch wireshark-common \
  tshark curl netcat-openbsd mosquitto-clients docker.io docker-compose-plugin
```

Install Python dependencies:

```bash
python3 -m venv ids_venv
source ids_venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/ahmed3bahaa/AI-Based-IDS-.git
cd AI-Based-IDS-
```

2. Copy the environment template and adjust the target IPs:

```bash
cp .env.example .env
nano .env
set -a
source .env
set +a
```

3. Start PostgreSQL:

```bash
docker compose up -d postgres
```

4. Run the attack/capture/conversion pipeline:

```bash
bash run_live_detection.sh
```

5. Start live Spark detection:

```bash
spark-submit --packages org.postgresql:postgresql:42.7.3 ids_streaming.py
```

6. Inspect generated alerts:

```bash
docker compose exec postgres psql -U mluser -d mlanalytics \
  -c "SELECT window_start, src_ip, dst_ip, rule_attack_name, flow_count, pkt_count FROM ids_alerts ORDER BY id DESC LIMIT 20;"
```

## How The Detection Works

`ids_streaming.py` watches `CSV_DIR` for new CICFlowMeter CSV files. Each file is read with the committed `cic_schema.json`, normalized to the feature names expected by the saved Spark pipeline, and passed through the `RF-20` model.

The model output is then aggregated by source, destination, and 10-second time windows. The rule layer promotes important patterns into final alerts:

- many unique destination ports becomes `PortScan`
- high flow or packet counts becomes `DoS_HighRate`
- repeated model votes become web, bot, infiltration, or Heartbleed alerts
- benign windows are ignored before writing to PostgreSQL

Thresholds are configurable through environment variables such as `PORTSCAN_PORTS`, `DOS_FLOWS`, `DOS_PKTS`, `WEB_VOTES`, and `BOT_VOTES`.

## Important Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `ESP_IP` | IoT victim/ESP32 IP address | `192.168.151.210` |
| `BROKER_IP` | MQTT broker IP address | `192.168.150.137` |
| `UPLINK` | VM interface that reaches the LAN | `enp0s3` |
| `IFACE` | Mininet NAT capture interface | `nat0-eth0` |
| `CSV_DIR` | Directory watched by Spark for CIC CSV files | `./csv` |
| `MODEL_PATH` | Saved Spark ML model path | `./RF-20` |
| `PG_HOST` / `PG_PORT` | PostgreSQL host and port | `localhost:5433` |
| `PG_TABLE` | Alert table name | `ids_alerts` |

## Safety Notice

Run traffic generation only in a lab network or against systems you own and have permission to test. The Mininet script can produce high request volumes by design.

## Project Status

This repository contains the live detection engine, attack/capture automation, saved model artifact, schema, and deployment helpers. Future improvements could add a dashboard, model retraining notebooks, CI checks, and sample anonymized CSV fixtures.

