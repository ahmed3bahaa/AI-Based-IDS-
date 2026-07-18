import glob
import os

from pyspark.sql import SparkSession

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.abspath(os.path.expanduser(os.getenv("CSV_DIR", os.path.join(BASE_DIR, "csv"))))
SCHEMA_OUT = os.path.abspath(os.path.expanduser(os.getenv("CIC_SCHEMA", os.path.join(BASE_DIR, "cic_schema.json"))))

spark = SparkSession.builder.appName("CIC-Schema").getOrCreate()

csvs = sorted(glob.glob(os.path.join(CSV_DIR, "*.csv")))
if not csvs:
    raise SystemExit(f"No CSV files found in {CSV_DIR}/")

sample = csvs[0]
df = spark.read.option("header", True).option("inferSchema", True).csv(sample)

with open(SCHEMA_OUT, "w", encoding="utf-8") as f:
    f.write(df.schema.json())

print("Schema written to:", SCHEMA_OUT)
spark.stop()
