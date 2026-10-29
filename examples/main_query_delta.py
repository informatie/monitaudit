# examples/main_query_delta.py

from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


DELTA_PATH = Path("dev_relatics/metadata/monitaudit_logs").resolve()
VIEW_NAME = "monitaudit_logs"


QUERIES = []

QUERIES.append( """ SELECT  MESSAGE, error_message FROM monitaudit_logs LIMIT 20 """ )
QUERIES.append( """ SELECT COUNT(*) AS record_count FROM monitaudit_logs """ )
QUERIES.append( """ SELECT  MESSAGE, application FROM monitaudit_logs LIMIT 20 """ )
x = 0

def create_spark() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("monitaudit-query-delta")
        .master("local[*]")
        .config(
            "spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension",
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )

    return configure_spark_with_delta_pip(builder).getOrCreate()


def main() -> None:
    print(f"Delta path: {DELTA_PATH}")

    if not DELTA_PATH.exists():
        raise FileNotFoundError(
            f"monitaudit Delta table does not exist: {DELTA_PATH}"
        )

    if not (DELTA_PATH / "_delta_log").exists():
        raise RuntimeError(
            f"Path exists but is not a Delta table: {DELTA_PATH}"
        )

    spark = create_spark()

    try:
        df = spark.read.format("delta").load(str(DELTA_PATH))

        print("\n=== monitaudit Delta schema ===")
        df.printSchema()

        # Make the Delta data available to Spark SQL.
        df.createOrReplaceTempView(VIEW_NAME)


        print(f"\n=== SQL query {x} ===")

        spark.sql(
            QUERIES[x - 1].upper()
        ).show(
            n=20,
            truncate=False,
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()