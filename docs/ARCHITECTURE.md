# Architecture

This project connects four stages into one IDS workflow: traffic generation, packet capture, flow extraction, and streaming detection.

## Data Flow

```text
Mininet hosts
  ├─ h1: HTTP requests
  ├─ h2: TCP socket traffic
  └─ h3: MQTT publish traffic
        ↓
Mininet NAT interface (nat0-eth0)
        ↓
dumpcap rotating PCAP capture
        ↓
CICFlowMeter CSV conversion
        ↓
Spark Structured Streaming
        ↓
RF-20 Spark ML Random Forest pipeline
        ↓
10-second alert aggregation rules
        ↓
PostgreSQL ids_alerts table
```

## Main Components

### `mininet_attack.py`

Creates a small Mininet tree topology with three hosts and one NAT node. The NAT node is connected to a selected physical uplink so Mininet hosts can reach the ESP32 and MQTT broker on the LAN.

Traffic roles:

- `h1` sends parallel HTTP requests to the ESP32.
- `h2` opens repeated TCP connections to the ESP32.
- `h3` publishes MQTT messages to the broker.

The script configures IP forwarding, NAT masquerading, and forwarding rules so replies can return to the Mininet hosts.

### `capture.sh`

Waits for the Mininet capture interface, then runs `dumpcap` with a BPF filter focused on the ESP32 and optional MQTT broker. Capture output is rotated by duration and file count to avoid a single large PCAP.

### `pcap_to_csv.sh`

Converts PCAP files into CICFlowMeter CSV output. The generated CSV files are the streaming input for Spark.

### `ids_streaming.py`

Runs the live IDS engine:

1. Reads CSV files as a stream with `cic_schema.json`.
2. Normalizes snake_case CICFlowMeter column names to the Spark model's expected feature names.
3. Adds missing model features as `0.0` to protect the VectorAssembler from null or missing fields.
4. Loads `RF-20` as a Spark `PipelineModel`.
5. Converts numeric predictions into human-readable attack names.
6. Aggregates predictions in 10-second windows by source and destination.
7. Writes non-benign alert windows to PostgreSQL using JDBC.

## Model Layer And Rule Layer

The Random Forest model gives per-flow predictions. Per-flow predictions can be noisy in a live lab, so the rule layer groups them into windows and raises alerts only when there is a stronger pattern.

Examples:

- `unique_dst_ports >= PORTSCAN_PORTS` raises `PortScan`.
- `flow_count >= DOS_FLOWS` or `pkt_count >= DOS_PKTS` raises `DoS_HighRate`.
- repeated web, bot, infiltration, or Heartbleed model votes raise their corresponding attack labels.

## Stored Alert Fields

The PostgreSQL table stores:

- window timing
- source and destination IPs
- final rule label and attack name
- flow and packet counts
- protocol-specific counts
- model vote counts for important attack families

That format is intentionally simple so dashboards can query the table directly.

