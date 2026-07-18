CREATE TABLE IF NOT EXISTS ids_alerts (
    id BIGSERIAL PRIMARY KEY,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    src_ip TEXT NOT NULL,
    dst_ip TEXT NOT NULL,
    rule_label_id INTEGER NOT NULL,
    rule_attack_name TEXT NOT NULL,
    flow_count BIGINT NOT NULL,
    pkt_count BIGINT,
    unique_dst_ports BIGINT,
    http_flows BIGINT,
    udp_flows BIGINT,
    ftp_flows BIGINT,
    ssh_flows BIGINT,
    bot_votes BIGINT,
    web_bf_votes BIGINT,
    web_xss_votes BIGINT,
    web_sql_votes BIGINT,
    infiltration_votes BIGINT,
    heartbleed_votes BIGINT,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ids_alerts_window
    ON ids_alerts (window_start, window_end);

CREATE INDEX IF NOT EXISTS idx_ids_alerts_attack
    ON ids_alerts (rule_attack_name);

CREATE INDEX IF NOT EXISTS idx_ids_alerts_hosts
    ON ids_alerts (src_ip, dst_ip);

