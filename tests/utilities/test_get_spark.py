from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

import monitaudit.utilities.get_spark as get_spark


def test_run_dbx_gets_or_creates_spark_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spark = MagicMock()

    builder = MagicMock()
    builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    result = get_spark.run_dbx()

    builder.getOrCreate.assert_called_once_with()

    assert result is spark


def test_run_dbx_sets_spark_log_level_to_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spark = MagicMock()

    builder = MagicMock()
    builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    get_spark.run_dbx()

    spark.sparkContext.setLogLevel.assert_called_once_with(
        "ERROR"
    )


def test_get_spark_session_sets_local_ip_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "SPARK_LOCAL_IP",
        raising=False,
    )

    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    assert (
        os.environ["SPARK_LOCAL_IP"]
        == "127.0.0.1"
    )


def test_get_spark_session_does_not_replace_existing_local_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "SPARK_LOCAL_IP",
        "192.168.1.100",
    )

    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    assert (
        os.environ["SPARK_LOCAL_IP"]
        == "192.168.1.100"
    )


def test_get_spark_session_sets_application_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    builder.appName.assert_called_once_with(
        "monitaudit"
    )


def test_get_spark_session_uses_local_master(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    builder.master.assert_called_once_with(
        "local[*]"
    )


def test_get_spark_session_disables_console_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    builder.config.assert_any_call(
        "spark.ui.showConsoleProgress",
        "false",
    )


def test_get_spark_session_enables_adaptive_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    builder.config.assert_any_call(
        "spark.sql.adaptive.enabled",
        "true",
    )

    builder.config.assert_any_call(
        "spark.sql.adaptive.coalescePartitions.enabled",
        "true",
    )


def test_get_spark_session_configures_delta_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    builder.config.assert_any_call(
        "spark.sql.extensions",
        "io.delta.sql.DeltaSparkSessionExtension",
    )

    builder.config.assert_any_call(
        "spark.sql.catalog.spark_catalog",
        "org.apache.spark.sql.delta.catalog.DeltaCatalog",
    )


def test_get_spark_session_enables_hive_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    builder.enableHiveSupport.assert_called_once_with()


def test_get_spark_session_passes_builder_to_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    configure_delta = MagicMock(
        return_value=delta_builder
    )

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        configure_delta,
    )

    get_spark.get_spark_session()

    configure_delta.assert_called_once_with(
        builder
    )


def test_get_spark_session_gets_or_creates_delta_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    result = get_spark.get_spark_session()

    delta_builder.getOrCreate.assert_called_once_with()

    assert result is spark


def test_get_spark_session_sets_log_level_to_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = MagicMock()
    spark = MagicMock()

    builder.appName.return_value = builder
    builder.master.return_value = builder
    builder.config.return_value = builder
    builder.enableHiveSupport.return_value = builder

    delta_builder = MagicMock()
    delta_builder.getOrCreate.return_value = spark

    monkeypatch.setattr(
        get_spark.SparkSession,
        "builder",
        builder,
    )

    monkeypatch.setattr(
        get_spark,
        "configure_spark_with_delta_pip",
        MagicMock(
            return_value=delta_builder
        ),
    )

    get_spark.get_spark_session()

    spark.sparkContext.setLogLevel.assert_called_once_with(
        "ERROR"
    )