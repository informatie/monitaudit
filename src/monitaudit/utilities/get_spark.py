import os

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


def run_dbx() -> SparkSession:
    spark = SparkSession.builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def get_spark_session() -> SparkSession:
    os.environ.setdefault(
        "SPARK_LOCAL_IP",
        "127.0.0.1",
    )

    builder = (
        SparkSession.builder
        .appName("monitaudit")
        .master("local[*]")
        .config(
            "spark.ui.showConsoleProgress",
            "false",
        )
        .config(
            "spark.sql.adaptive.enabled",
            "true",
        )
        .config(
            "spark.sql.adaptive.coalescePartitions.enabled",
            "true",
        )
        .config(
            "spark.sql.extensions",
            "io.delta.sql.DeltaSparkSessionExtension",
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .enableHiveSupport()
    )

    spark = configure_spark_with_delta_pip(
        builder
    ).getOrCreate()

    spark.sparkContext.setLogLevel("ERROR")

    return spark