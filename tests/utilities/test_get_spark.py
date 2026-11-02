# tests/utilities/test_get_spark.py

from __future__ import annotations

import importlib
import os
from typing import Any

import pytest

get_spark_module = importlib.import_module(
    "monitaudit.utilities.get_spark"
)

from monitaudit.utilities.get_spark import (
    get_spark_session,
    run_dbx,
)


class FakeSparkContext:
    def __init__(self) -> None:
        self.log_levels: list[str] = []

    def setLogLevel(
        self,
        level: str,
    ) -> None:
        self.log_levels.append(level)


class FakeSparkSession:
    def __init__(self) -> None:
        self.sparkContext = FakeSparkContext()


class FakeBuilder:
    def __init__(
        self,
        spark: FakeSparkSession,
    ) -> None:
        self.spark = spark

        self.app_name_calls: list[str] = []
        self.master_calls: list[str] = []
        self.config_calls: list[
            tuple[str, Any]
        ] = []

        self.enable_hive_support_count = 0
        self.get_or_create_count = 0

    def appName(
        self,
        name: str,
    ) -> FakeBuilder:
        self.app_name_calls.append(name)
        return self

    def master(
        self,
        master: str,
    ) -> FakeBuilder:
        self.master_calls.append(master)
        return self

    def config(
        self,
        key: str,
        value: Any,
    ) -> FakeBuilder:
        self.config_calls.append(
            (
                key,
                value,
            )
        )
        return self

    def enableHiveSupport(
        self,
    ) -> FakeBuilder:
        self.enable_hive_support_count += 1
        return self

    def getOrCreate(
        self,
    ) -> FakeSparkSession:
        self.get_or_create_count += 1
        return self.spark


class TestRunDbx:
    def test_returns_spark_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        result = run_dbx()

        assert result is spark

    def test_uses_get_or_create(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        run_dbx()

        assert builder.get_or_create_count == 1

    def test_sets_spark_log_level_to_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        run_dbx()

        assert spark.sparkContext.log_levels == [
            "ERROR"
        ]

    def test_does_not_configure_local_builder(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        run_dbx()

        assert builder.app_name_calls == []
        assert builder.master_calls == []
        assert builder.config_calls == []
        assert builder.enable_hive_support_count == 0

    def test_propagates_get_or_create_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected_exception = RuntimeError(
            "Spark unavailable"
        )

        class FailingBuilder:
            def getOrCreate(self) -> FakeSparkSession:
                raise expected_exception

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            FailingBuilder(),
        )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            run_dbx()

        assert exception_info.value is expected_exception

    def test_propagates_set_log_level_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected_exception = RuntimeError(
            "cannot set log level"
        )

        class FailingSparkContext:
            def setLogLevel(
                self,
                _level: str,
            ) -> None:
                raise expected_exception

        class FailingSpark:
            def __init__(self) -> None:
                self.sparkContext = FailingSparkContext()

        spark = FailingSpark()

        class Builder:
            def getOrCreate(self) -> FailingSpark:
                return spark

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            Builder(),
        )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            run_dbx()

        assert exception_info.value is expected_exception


class TestGetSparkSessionEnvironment:
    def test_sets_default_spark_local_ip(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv(
            "SPARK_LOCAL_IP",
            raising=False,
        )

        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        get_spark_session()

        assert (
            os.environ["SPARK_LOCAL_IP"]
            == "127.0.0.1"
        )

    def test_preserves_existing_spark_local_ip(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "SPARK_LOCAL_IP",
            "192.168.1.10",
        )

        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        get_spark_session()

        assert (
            os.environ["SPARK_LOCAL_IP"]
            == "192.168.1.10"
        )

    @pytest.mark.parametrize(
        "existing_value",
        [
            "",
            "localhost",
            "10.0.0.1",
            "127.0.0.2",
        ],
    )
    def test_setdefault_does_not_replace_existing_value(
        self,
        monkeypatch: pytest.MonkeyPatch,
        existing_value: str,
    ) -> None:
        monkeypatch.setenv(
            "SPARK_LOCAL_IP",
            existing_value,
        )

        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        get_spark_session()

        assert (
            os.environ["SPARK_LOCAL_IP"]
            == existing_value
        )


class TestGetSparkSessionBuilder:
    @pytest.fixture
    def configured_builder(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> tuple[
        FakeBuilder,
        FakeSparkSession,
    ]:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        return (
            builder,
            spark,
        )

    def test_sets_application_name(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert builder.app_name_calls == [
            "monitaudit"
        ]

    def test_sets_local_master(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert builder.master_calls == [
            "local[*]"
        ]

    def test_disables_console_progress(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert (
            "spark.ui.showConsoleProgress",
            "false",
        ) in builder.config_calls

    def test_enables_adaptive_execution(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert (
            "spark.sql.adaptive.enabled",
            "true",
        ) in builder.config_calls

    def test_enables_adaptive_partition_coalescing(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert (
            (
                "spark.sql.adaptive."
                "coalescePartitions.enabled"
            ),
            "true",
        ) in builder.config_calls

    def test_sets_delta_extension(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert (
            "spark.sql.extensions",
            (
                "io.delta.sql."
                "DeltaSparkSessionExtension"
            ),
        ) in builder.config_calls

    def test_sets_delta_catalog(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert (
            "spark.sql.catalog.spark_catalog",
            (
                "org.apache.spark.sql.delta."
                "catalog.DeltaCatalog"
            ),
        ) in builder.config_calls

    def test_sets_all_expected_configuration_values(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert builder.config_calls == [
            (
                "spark.ui.showConsoleProgress",
                "false",
            ),
            (
                "spark.sql.adaptive.enabled",
                "true",
            ),
            (
                (
                    "spark.sql.adaptive."
                    "coalescePartitions.enabled"
                ),
                "true",
            ),
            (
                "spark.sql.extensions",
                (
                    "io.delta.sql."
                    "DeltaSparkSessionExtension"
                ),
            ),
            (
                "spark.sql.catalog.spark_catalog",
                (
                    "org.apache.spark.sql.delta."
                    "catalog.DeltaCatalog"
                ),
            ),
        ]

    def test_enables_hive_support(
        self,
        configured_builder: tuple[
            FakeBuilder,
            FakeSparkSession,
        ],
    ) -> None:
        builder, _ = configured_builder

        get_spark_session()

        assert (
            builder.enable_hive_support_count
            == 1
        )


class TestDeltaConfiguration:
    def test_passes_builder_to_delta_configuration(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        received: list[object] = []

        def fake_configure(
            value: object,
        ) -> FakeBuilder:
            received.append(value)
            return builder

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            fake_configure,
        )

        get_spark_session()

        assert received == [builder]

    def test_calls_get_or_create_on_delta_builder(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        original_spark = FakeSparkSession()
        original_builder = FakeBuilder(
            original_spark
        )

        configured_spark = FakeSparkSession()
        configured_builder = FakeBuilder(
            configured_spark
        )

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            original_builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda _builder: configured_builder,
        )

        result = get_spark_session()

        assert (
            original_builder.get_or_create_count
            == 0
        )
        assert (
            configured_builder.get_or_create_count
            == 1
        )
        assert result is configured_spark

    def test_delta_configuration_called_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        calls = 0

        def configure(
            value: FakeBuilder,
        ) -> FakeBuilder:
            nonlocal calls
            calls += 1
            return value

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            configure,
        )

        get_spark_session()

        assert calls == 1

    def test_propagates_delta_configuration_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        expected_exception = RuntimeError(
            "Delta configuration failed"
        )

        def failing_configure(
            _builder: FakeBuilder,
        ) -> FakeBuilder:
            raise expected_exception

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            failing_configure,
        )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            get_spark_session()

        assert (
            exception_info.value
            is expected_exception
        )

        assert builder.get_or_create_count == 0


class TestLocalSparkCreation:
    def test_returns_created_spark_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        result = get_spark_session()

        assert result is spark

    def test_calls_get_or_create_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        get_spark_session()

        assert builder.get_or_create_count == 1

    def test_sets_log_level_to_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()
        builder = FakeBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        get_spark_session()

        assert spark.sparkContext.log_levels == [
            "ERROR"
        ]

    def test_log_level_is_set_after_spark_creation(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        operations: list[str] = []

        class OrderedSparkContext:
            def setLogLevel(
                self,
                level: str,
            ) -> None:
                operations.append(
                    f"log-level:{level}"
                )

        class OrderedSpark:
            def __init__(self) -> None:
                self.sparkContext = (
                    OrderedSparkContext()
                )

        spark = OrderedSpark()

        class OrderedBuilder(FakeBuilder):
            def __init__(self) -> None:
                super().__init__(  # type: ignore[arg-type]
                    spark
                )

            def getOrCreate(
                self,
            ) -> OrderedSpark:
                operations.append(
                    "get-or-create"
                )
                return spark

        builder = OrderedBuilder()

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        get_spark_session()

        assert operations == [
            "get-or-create",
            "log-level:ERROR",
        ]

    def test_propagates_get_or_create_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        spark = FakeSparkSession()

        class FailingBuilder(
            FakeBuilder
        ):
            def getOrCreate(
                self,
            ) -> FakeSparkSession:
                raise RuntimeError(
                    "Spark creation failed"
                )

        builder = FailingBuilder(spark)

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        with pytest.raises(
            RuntimeError,
            match="Spark creation failed",
        ):
            get_spark_session()

    def test_propagates_set_log_level_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected_exception = RuntimeError(
            "cannot configure Spark logging"
        )

        class FailingSparkContext:
            def setLogLevel(
                self,
                _level: str,
            ) -> None:
                raise expected_exception

        class Spark:
            def __init__(self) -> None:
                self.sparkContext = (
                    FailingSparkContext()
                )

        spark = Spark()

        class Builder(FakeBuilder):
            def __init__(self) -> None:
                super().__init__(  # type: ignore[arg-type]
                    spark
                )

            def getOrCreate(
                self,
            ) -> Spark:
                return spark

        builder = Builder()

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            get_spark_session()

        assert (
            exception_info.value
            is expected_exception
        )


class TestBuilderCallOrder:
    def test_builder_is_configured_in_expected_order(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        operations: list[
            tuple[str, Any]
        ] = []

        spark = FakeSparkSession()

        class OrderedBuilder:
            def appName(
                self,
                value: str,
            ) -> OrderedBuilder:
                operations.append(
                    (
                        "appName",
                        value,
                    )
                )
                return self

            def master(
                self,
                value: str,
            ) -> OrderedBuilder:
                operations.append(
                    (
                        "master",
                        value,
                    )
                )
                return self

            def config(
                self,
                key: str,
                value: Any,
            ) -> OrderedBuilder:
                operations.append(
                    (
                        key,
                        value,
                    )
                )
                return self

            def enableHiveSupport(
                self,
            ) -> OrderedBuilder:
                operations.append(
                    (
                        "enableHiveSupport",
                        None,
                    )
                )
                return self

            def getOrCreate(
                self,
            ) -> FakeSparkSession:
                return spark

        builder = OrderedBuilder()

        monkeypatch.setattr(
            get_spark_module.SparkSession,
            "builder",
            builder,
        )

        monkeypatch.setattr(
            get_spark_module,
            "configure_spark_with_delta_pip",
            lambda value: value,
        )

        get_spark_session()

        assert operations == [
            (
                "appName",
                "monitaudit",
            ),
            (
                "master",
                "local[*]",
            ),
            (
                "spark.ui.showConsoleProgress",
                "false",
            ),
            (
                "spark.sql.adaptive.enabled",
                "true",
            ),
            (
                (
                    "spark.sql.adaptive."
                    "coalescePartitions.enabled"
                ),
                "true",
            ),
            (
                "spark.sql.extensions",
                (
                    "io.delta.sql."
                    "DeltaSparkSessionExtension"
                ),
            ),
            (
                "spark.sql.catalog.spark_catalog",
                (
                    "org.apache.spark.sql.delta."
                    "catalog.DeltaCatalog"
                ),
            ),
            (
                "enableHiveSupport",
                None,
            ),
        ]