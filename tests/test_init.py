# tests/test_init.py

from __future__ import annotations

from typing import Any, cast

import pytest

import monitaudit
from monitaudit import Monitaudit


EXPECTED_PUBLIC_API = {
    "ConsoleSink",
    "DeltaSink",
    "FileSink",
    "JsonSink",
    "LogContext",
    "Monitaudit",
    "monitauditLogger",
    "build_monitaudit",
    "monitaudit_init",
}


class TestVersion:
    def test_version(
        self,
    ) -> None:
        assert monitaudit.__version__ == "1.2.5"


class TestPublicApi:
    def test_all_matches_public_api(
        self,
    ) -> None:
        assert set(
            monitaudit.__all__
        ) == EXPECTED_PUBLIC_API

        assert len(
            monitaudit.__all__
        ) == len(
            EXPECTED_PUBLIC_API
        )

    @pytest.mark.parametrize(
        "name",
        sorted(
            EXPECTED_PUBLIC_API
        ),
    )
    def test_public_name_exists(
        self,
        name: str,
    ) -> None:
        assert hasattr(
            monitaudit,
            name,
        )

        assert (
            getattr(
                monitaudit,
                name,
            )
            is not None
        )

    def test_version_is_not_in_all(
        self,
    ) -> None:
        assert (
            "__version__"
            not in monitaudit.__all__
        )


class TestExportIdentity:
    @pytest.mark.parametrize(
        (
            "package_value",
            "source_value",
        ),
        [
            pytest.param(
                monitaudit.ConsoleSink,
                __import__(
                    "monitaudit.sinks",
                    fromlist=[
                        "ConsoleSink",
                    ],
                ).ConsoleSink,
                id="ConsoleSink",
            ),
            pytest.param(
                monitaudit.DeltaSink,
                __import__(
                    "monitaudit.sinks",
                    fromlist=[
                        "DeltaSink",
                    ],
                ).DeltaSink,
                id="DeltaSink",
            ),
            pytest.param(
                monitaudit.FileSink,
                __import__(
                    "monitaudit.sinks",
                    fromlist=[
                        "FileSink",
                    ],
                ).FileSink,
                id="FileSink",
            ),
            pytest.param(
                monitaudit.JsonSink,
                __import__(
                    "monitaudit.sinks",
                    fromlist=[
                        "JsonSink",
                    ],
                ).JsonSink,
                id="JsonSink",
            ),
        ],
    )
    def test_sink_export_identity(
        self,
        package_value: object,
        source_value: object,
    ) -> None:
        assert (
            package_value
            is source_value
        )

    def test_log_context_export_identity(
        self,
    ) -> None:
        from monitaudit.models.context import (
            LogContext,
        )

        assert (
            monitaudit.LogContext
            is LogContext
        )

    def test_monitaudit_export_identity(
        self,
    ) -> None:
        from monitaudit.models.monitaudit import (
            Monitaudit as ModelMonitaudit,
        )

        assert (
            monitaudit.Monitaudit
            is ModelMonitaudit
        )

    def test_logger_export_identity(
        self,
    ) -> None:
        from monitaudit.logger import (
            monitauditLogger,
        )

        assert (
            monitaudit.monitauditLogger
            is monitauditLogger
        )

    def test_build_export_identity(
        self,
    ) -> None:
        from monitaudit.utilities.build_monitaudit import (
            build_monitaudit,
        )

        assert (
            monitaudit.build_monitaudit
            is build_monitaudit
        )


class TestMonitauditInit:
    def test_returns_build_result_and_calls_once(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected = cast(
            Monitaudit,
            object(),
        )
        calls = 0

        def fake_build() -> Monitaudit:
            nonlocal calls

            calls += 1

            return expected

        monkeypatch.setattr(
            monitaudit,
            "build_monitaudit",
            fake_build,
        )

        result = (
            monitaudit.monitaudit_init()
        )

        assert result is expected
        assert calls == 1

    def test_calls_build_without_arguments(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected = cast(
            Monitaudit,
            object(),
        )

        calls: list[
            tuple[
                tuple[Any, ...],
                dict[str, Any],
            ]
        ] = []

        def fake_build(
            *args: Any,
            **kwargs: Any,
        ) -> Monitaudit:
            calls.append(
                (
                    args,
                    kwargs,
                )
            )

            return expected

        monkeypatch.setattr(
            monitaudit,
            "build_monitaudit",
            fake_build,
        )

        monitaudit.monitaudit_init()

        assert calls == [
            (
                (),
                {},
            )
        ]

    def test_propagates_build_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected = RuntimeError(
            "configuration failed"
        )

        def fake_build() -> Monitaudit:
            raise expected

        monkeypatch.setattr(
            monitaudit,
            "build_monitaudit",
            fake_build,
        )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            monitaudit.monitaudit_init()

        assert (
            exception_info.value
            is expected
        )


class TestDirectImport:
    def test_monitaudit_init_can_be_imported_directly(
        self,
    ) -> None:
        from monitaudit import (
            monitaudit_init,
        )

        assert (
            monitaudit_init
            is monitaudit.monitaudit_init
        )

    def test_build_monitaudit_can_be_imported_directly(
        self,
    ) -> None:
        from monitaudit import (
            build_monitaudit,
        )

        assert (
            build_monitaudit
            is monitaudit.build_monitaudit
        )