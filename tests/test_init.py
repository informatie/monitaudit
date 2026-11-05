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
        sorted(EXPECTED_PUBLIC_API),
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
        assert package_value is source_value

    def test_log_context_export_identity(
        self,
    ) -> None:
        from monitaudit.models.context import LogContext

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
        from monitaudit.logger import monitauditLogger

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

        calls: list[dict[str, Any]] = []

        def fake_build(
            **kwargs: Any,
        ) -> Monitaudit:
            calls.append(kwargs)
            return expected

        monkeypatch.setattr(
            monitaudit,
            "build_monitaudit",
            fake_build,
        )

        result = monitaudit.monitaudit_init()

        assert result is expected
        assert calls == [
            {
                "correlation_id": None,
            }
        ]

    def test_passes_none_correlation_id_by_default(
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

        result = monitaudit.monitaudit_init()

        assert result is expected

        assert calls == [
            (
                (),
                {
                    "correlation_id": None,
                },
            )
        ]

    def test_passes_explicit_correlation_id(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected = cast(
            Monitaudit,
            object(),
        )

        received: dict[str, Any] = {}

        def fake_build(
            **kwargs: Any,
        ) -> Monitaudit:
            received.update(kwargs)
            return expected

        monkeypatch.setattr(
            monitaudit,
            "build_monitaudit",
            fake_build,
        )

        result = monitaudit.monitaudit_init(
            correlation_id="RELATICS-12345",
        )

        assert result is expected

        assert received == {
            "correlation_id": "RELATICS-12345",
        }

    @pytest.mark.parametrize(
        "correlation_id",
        [
            "RELATICS-12345",
            "550e8400-e29b-41d4-a716-446655440000",
            "application-run-001",
        ],
    )
    def test_preserves_correlation_id_exactly(
        self,
        monkeypatch: pytest.MonkeyPatch,
        correlation_id: str,
    ) -> None:
        expected = cast(
            Monitaudit,
            object(),
        )

        received: list[str | None] = []

        def fake_build(
            *,
            correlation_id: str | None = None,
        ) -> Monitaudit:
            received.append(
                correlation_id
            )

            return expected

        monkeypatch.setattr(
            monitaudit,
            "build_monitaudit",
            fake_build,
        )

        monitaudit.monitaudit_init(
            correlation_id=correlation_id,
        )

        assert received == [
            correlation_id,
        ]

    def test_does_not_generate_correlation_id_itself(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected = cast(
            Monitaudit,
            object(),
        )

        received: list[str | None] = []

        def fake_build(
            *,
            correlation_id: str | None = None,
        ) -> Monitaudit:
            received.append(
                correlation_id
            )

            return expected

        monkeypatch.setattr(
            monitaudit,
            "build_monitaudit",
            fake_build,
        )

        monitaudit.monitaudit_init()

        assert received == [
            None,
        ]

    def test_propagates_build_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected = RuntimeError(
            "configuration failed"
        )

        def fake_build(
            *,
            correlation_id: str | None = None,
        ) -> Monitaudit:
            del correlation_id
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
        from monitaudit import monitaudit_init

        assert (
            monitaudit_init
            is monitaudit.monitaudit_init
        )

    def test_build_monitaudit_can_be_imported_directly(
        self,
    ) -> None:
        from monitaudit import build_monitaudit

        assert (
            build_monitaudit
            is monitaudit.build_monitaudit
        )