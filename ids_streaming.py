import os
import json
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql import functions as F
from pyspark.sql.types import StructType

# ----------------------------
# Paths / env
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ESP_IP = os.getenv("ESP_IP", "192.168.151.210")

CSV_DIR = os.path.abspath(os.path.expanduser(os.getenv("CSV_DIR", os.path.join(BASE_DIR, "csv"))))
CHECKPOINT = os.path.abspath(os.path.expanduser(os.getenv("CHECKPOINT", os.path.join(BASE_DIR, "checkpoints/ids_stream"))))


PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5433")
PG_DB   = os.getenv("PG_DB", "mlanalytics")
PG_USER = os.getenv("PG_USER", "mluser")
PG_PASS = os.getenv("PG_PASS", "mlpass")
PG_TABLE = os.getenv("PG_TABLE", "ids_alerts")

MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(BASE_DIR, "RF-20"))
if not os.path.isabs(MODEL_PATH):
    MODEL_PATH = os.path.join(BASE_DIR, MODEL_PATH)

SCHEMA_PATH = os.getenv("CIC_SCHEMA", os.path.join(BASE_DIR, "cic_schema.json"))
if not os.path.isabs(SCHEMA_PATH):
    SCHEMA_PATH = os.path.join(BASE_DIR, SCHEMA_PATH)
if not os.path.exists(SCHEMA_PATH):
    alt = os.path.join(BASE_DIR, "cic_Schema.json")
    if os.path.exists(alt):
        SCHEMA_PATH = alt


id_to_label = {
  0: "BENIGN",
  1: "DoS_Hulk",
  2: "PortScan",
  3: "DDoS",
  4: "DoS_GoldenEye",
  5: "FTP_Patator",
  6: "SSH_Patator",
  7: "DoS_slowloris",
  8: "DoS_Slowhttptest",
  9: "Bot",
  10: "Web_Attack_Brute_Force",
  11: "Web_Attack_XSS",
  12: "Web_Attack_SQL_Injection",
  13: "Infiltration",
  14: "Heartbleed",
  15: "DoS_UDP_Flood",
}


spark = (
  SparkSession.builder
    .appName("IDS-Live-ESP32")
    .getOrCreate()
)
spark.sparkContext.setLogLevel(os.getenv("SPARK_LOG_LEVEL", "WARN"))


_map_items = []
for k, v in id_to_label.items():
    _map_items.append(F.lit(int(k)))
    _map_items.append(F.lit(v))
LABEL_MAP = F.create_map(*_map_items)


if not os.path.exists(SCHEMA_PATH):
    raise RuntimeError(
        f"Missing schema file: {SCHEMA_PATH}\n"
        "Create it once using a sample CSV:\n"
        "  spark.read.csv(sample, header=True, inferSchema=True).schema.json()"
    )
schema = StructType.fromJson(json.loads(open(SCHEMA_PATH, "r").read()))


model = PipelineModel.load(MODEL_PATH)

assembler = None
for stage in model.stages:
    if stage.__class__.__name__ == "VectorAssembler":
        assembler = stage
        break
if assembler is None:
    raise RuntimeError("No VectorAssembler found in model stages")

feature_cols = assembler.getInputCols()


def rename_if_exists(df, old, new):
    return df.withColumnRenamed(old, new) if (old in df.columns and new not in df.columns) else df

def col_any(df, *names):
    for n in names:
        if n in df.columns:
            return F.col(n)
    raise RuntimeError(f"Missing required column. Tried: {names}. Available: {df.columns}")


rename_map = {
  "dst_port":"Dst Port","protocol":"Protocol","flow_duration":"Flow Duration",
  "tot_fwd_pkts":"Tot Fwd Pkts","tot_bwd_pkts":"Tot Bwd Pkts",
  "totlen_fwd_pkts":"TotLen Fwd Pkts","totlen_bwd_pkts":"TotLen Bwd Pkts",
  "fwd_pkt_len_max":"Fwd Pkt Len Max","fwd_pkt_len_min":"Fwd Pkt Len Min",
  "fwd_pkt_len_mean":"Fwd Pkt Len Mean","fwd_pkt_len_std":"Fwd Pkt Len Std",
  "bwd_pkt_len_max":"Bwd Pkt Len Max","bwd_pkt_len_min":"Bwd Pkt Len Min",
  "bwd_pkt_len_mean":"Bwd Pkt Len Mean","bwd_pkt_len_std":"Bwd Pkt Len Std",
  "flow_byts_s":"Flow Byts/s","flow_pkts_s":"Flow Pkts/s",
  "flow_iat_mean":"Flow IAT Mean","flow_iat_std":"Flow IAT Std",
  "flow_iat_max":"Flow IAT Max","flow_iat_min":"Flow IAT Min",
  "fwd_iat_tot":"Fwd IAT Tot","fwd_iat_mean":"Fwd IAT Mean","fwd_iat_std":"Fwd IAT Std",
  "fwd_iat_max":"Fwd IAT Max","fwd_iat_min":"Fwd IAT Min",
  "bwd_iat_tot":"Bwd IAT Tot","bwd_iat_mean":"Bwd IAT Mean","bwd_iat_std":"Bwd IAT Std",
  "bwd_iat_max":"Bwd IAT Max","bwd_iat_min":"Bwd IAT Min",
  "fwd_psh_flags":"Fwd PSH Flags","bwd_psh_flags":"Bwd PSH Flags",
  "fwd_urg_flags":"Fwd URG Flags","bwd_urg_flags":"Bwd URG Flags",
  "fwd_header_len":"Fwd Header Len","bwd_header_len":"Bwd Header Len",
  "fwd_pkts_s":"Fwd Pkts/s","bwd_pkts_s":"Bwd Pkts/s",
  "pkt_len_min":"Pkt Len Min","pkt_len_max":"Pkt Len Max","pkt_len_mean":"Pkt Len Mean",
  "pkt_len_std":"Pkt Len Std","pkt_len_var":"Pkt Len Var",
  "fin_flag_cnt":"FIN Flag Cnt","syn_flag_cnt":"SYN Flag Cnt","rst_flag_cnt":"RST Flag Cnt",
  "psh_flag_cnt":"PSH Flag Cnt","ack_flag_cnt":"ACK Flag Cnt","urg_flag_cnt":"URG Flag Cnt",
  "cwe_flag_count":"CWE Flag Count","ece_flag_cnt":"ECE Flag Cnt",
  "down_up_ratio":"Down/Up Ratio","pkt_size_avg":"Pkt Size Avg",
  "fwd_seg_size_avg":"Fwd Seg Size Avg","bwd_seg_size_avg":"Bwd Seg Size Avg",
  "fwd_byts_b_avg":"Fwd Byts/b Avg","fwd_pkts_b_avg":"Fwd Pkts/b Avg","fwd_blk_rate_avg":"Fwd Blk Rate Avg",
  "bwd_byts_b_avg":"Bwd Byts/b Avg","bwd_pkts_b_avg":"Bwd Pkts/b Avg","bwd_blk_rate_avg":"Bwd Blk Rate Avg",
  "subflow_fwd_pkts":"Subflow Fwd Pkts","subflow_fwd_byts":"Subflow Fwd Byts",
  "subflow_bwd_pkts":"Subflow Bwd Pkts","subflow_bwd_byts":"Subflow Bwd Byts",
  "init_fwd_win_byts":"Init Fwd Win Byts","init_bwd_win_byts":"Init Bwd Win Byts",
  "fwd_act_data_pkts":"Fwd Act Data Pkts","fwd_seg_size_min":"Fwd Seg Size Min",
  "active_mean":"Active Mean","active_std":"Active Std","active_max":"Active Max","active_min":"Active Min",
  "idle_mean":"Idle Mean","idle_std":"Idle Std","idle_max":"Idle Max","idle_min":"Idle Min",
}


df_raw = (
    spark.readStream
      .schema(schema)
      .option("header", "true")
      .csv(CSV_DIR)
)

df = df_raw
df = rename_if_exists(df, "Src IP", "src_ip")
df = rename_if_exists(df, "Dst IP", "dst_ip")


ts_str = col_any(df, "Timestamp", "timestamp")
df = df.withColumn(
    "ts",
    F.coalesce(
        F.to_timestamp(ts_str, "dd/MM/yyyy HH:mm:ss"),
        F.to_timestamp(ts_str, "yyyy-MM-dd HH:mm:ss"),
        F.to_timestamp(ts_str)
    )
).filter(F.col("ts").isNotNull())

# Only flows TO ESP (victim)
df = df.filter(F.col("dst_ip") == ESP_IP)

# Apply snake_case -> CIC names (only if needed)
for old, new in rename_map.items():
    if old in df.columns and new not in df.columns:
        df = df.withColumnRenamed(old, new)

# Ensure all model features exist + are double + NO NULLS (fixes VectorAssembler null crash)
for c in feature_cols:
    if c not in df.columns:
        df = df.withColumn(c, F.lit(0.0))
    df = df.withColumn(c, F.col(c).cast("double"))

df = df.fillna(0.0, subset=feature_cols)

# ----------------------------
# Apply model + attack name without UDF
# ----------------------------
pred = model.transform(df)
pred = pred.withColumn("prediction_int", F.col("prediction").cast("int"))
pred = pred.withColumn(
    "attack_name",
    F.coalesce(LABEL_MAP.getItem(F.col("prediction_int")), F.lit("UNKNOWN"))
).drop("prediction_int")

# ----------------------------
# Rules inputs
# ----------------------------
dst_port = col_any(pred, "Dst Port", "dst_port").cast("int")
proto = col_any(pred, "Protocol", "protocol").cast("int")

is_http = dst_port.isin(80, 443, 8080)
is_ftp  = (dst_port == 21)
is_ssh  = (dst_port == 22)
is_udp  = (proto == 17)

is_bot  = (F.col("attack_name") == "Bot")
is_wbf  = (F.col("attack_name") == "Web_Attack_Brute_Force")
is_xss  = (F.col("attack_name") == "Web_Attack_XSS")
is_sql  = (F.col("attack_name") == "Web_Attack_SQL_Injection")
is_infl = (F.col("attack_name") == "Infiltration")
is_hb   = (F.col("attack_name") == "Heartbleed")

pkt_expr = F.lit(0)
if "Tot Fwd Pkts" in pred.columns and "Tot Bwd Pkts" in pred.columns:
    pkt_expr = (F.col("Tot Fwd Pkts").cast("int") + F.col("Tot Bwd Pkts").cast("int"))

# ----------------------------
# Window aggregation (10s)
# ----------------------------
w = (
    pred.groupBy(
        F.window("ts", "10 seconds").alias("w"),
        F.col("src_ip"),
        F.col("dst_ip"),
    )
    .agg(
        F.count(F.lit(1)).alias("flow_count"),
        F.sum(pkt_expr).alias("pkt_count"),
        F.approx_count_distinct(dst_port).alias("unique_dst_ports"),
        F.sum(F.when(is_http, 1).otherwise(0)).alias("http_flows"),
        F.sum(F.when(is_udp, 1).otherwise(0)).alias("udp_flows"),
        F.sum(F.when(is_ftp, 1).otherwise(0)).alias("ftp_flows"),
        F.sum(F.when(is_ssh, 1).otherwise(0)).alias("ssh_flows"),
        F.sum(F.when(is_bot, 1).otherwise(0)).alias("bot_votes"),
        F.sum(F.when(is_wbf, 1).otherwise(0)).alias("web_bf_votes"),
        F.sum(F.when(is_xss, 1).otherwise(0)).alias("web_xss_votes"),
        F.sum(F.when(is_sql, 1).otherwise(0)).alias("web_sql_votes"),
        F.sum(F.when(is_infl, 1).otherwise(0)).alias("infiltration_votes"),
        F.sum(F.when(is_hb, 1).otherwise(0)).alias("heartbleed_votes"),
    )
    .withColumn("window_start", F.col("w.start"))
    .withColumn("window_end",   F.col("w.end"))
    .drop("w")
)

# ----------------------------
# Rule engine thresholds
# ----------------------------
PORTSCAN_PORTS = int(os.getenv("PORTSCAN_PORTS", "50"))
DOS_FLOWS      = int(os.getenv("DOS_FLOWS", "200"))
DOS_PKTS       = int(os.getenv("DOS_PKTS", "1000"))
WEB_VOTES      = int(os.getenv("WEB_VOTES", "5"))
BOT_VOTES      = int(os.getenv("BOT_VOTES", "5"))
HB_VOTES       = int(os.getenv("HB_VOTES", "1"))
INFL_VOTES     = int(os.getenv("INFL_VOTES", "2"))

w = w.withColumn(
    "rule_attack_name",
    F.when(F.col("heartbleed_votes") >= HB_VOTES, F.lit("Heartbleed"))
     .when(F.col("infiltration_votes") >= INFL_VOTES, F.lit("Infiltration"))
     .when(F.col("web_sql_votes") >= WEB_VOTES, F.lit("Web_Attack_SQL_Injection"))
     .when(F.col("web_xss_votes") >= WEB_VOTES, F.lit("Web_Attack_XSS"))
     .when(F.col("web_bf_votes") >= WEB_VOTES, F.lit("Web_Attack_Brute_Force"))
     .when(F.col("bot_votes") >= BOT_VOTES, F.lit("Bot"))
     .when(F.col("unique_dst_ports") >= PORTSCAN_PORTS, F.lit("PortScan"))
     .when((F.col("flow_count") >= DOS_FLOWS) | (F.col("pkt_count") >= DOS_PKTS), F.lit("DoS_HighRate"))
     .otherwise(F.lit("BENIGN"))
)

w = w.withColumn(
    "rule_label_id",
    F.when(F.col("rule_attack_name") == "BENIGN", F.lit(0))
     .when(F.col("rule_attack_name") == "DoS_HighRate", F.lit(1))
     .when(F.col("rule_attack_name") == "PortScan", F.lit(2))
     .when(F.col("rule_attack_name") == "Bot", F.lit(9))
     .when(F.col("rule_attack_name") == "Web_Attack_Brute_Force", F.lit(10))
     .when(F.col("rule_attack_name") == "Web_Attack_XSS", F.lit(11))
     .when(F.col("rule_attack_name") == "Web_Attack_SQL_Injection", F.lit(12))
     .when(F.col("rule_attack_name") == "Infiltration", F.lit(13))
     .when(F.col("rule_attack_name") == "Heartbleed", F.lit(14))
     .otherwise(F.lit(-1))
)

# ----------------------------
# Postgres writer
# ----------------------------
jdbc_url = f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"
jdbc_props = {"user": PG_USER, "password": PG_PASS, "driver": "org.postgresql.Driver"}

def write_batch(batch_df, batch_id: int):
    out = (
        batch_df
        .filter(F.col("rule_attack_name") != "BENIGN")
        .select(
            "window_start","window_end","src_ip","dst_ip",
            "rule_label_id","rule_attack_name",
            "flow_count","pkt_count","unique_dst_ports",
            "http_flows","udp_flows","ftp_flows","ssh_flows",
            "bot_votes","web_bf_votes","web_xss_votes","web_sql_votes",
            "infiltration_votes","heartbleed_votes"
        )
    )

    if out.rdd.isEmpty():
        return

    out.write.mode("append").jdbc(url=jdbc_url, table=PG_TABLE, properties=jdbc_props)

query = (
    w.writeStream
     .outputMode("update")
     .foreachBatch(write_batch)
     .option("checkpointLocation", CHECKPOINT)
     .start()
)

query.awaitTermination()
