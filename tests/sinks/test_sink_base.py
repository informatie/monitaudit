from __future__ import annotations

import pytest

from monitaudit.models.base import BaseLog
from monitaudit.models.context import LogContext
from monitaudit.models.log import InfoLog
from monitaudit.sinks.base import Sink


@pytest.fixture
def context() -> LogContext:
    return LogContext(
        application="monitaudit-test",
        environment="dev",
        correlation_id="correlation-123",
        run_id="run-456",
    )


def test_sink_is_abstract() -> None:
    with pytest.raises(
        TypeError,
        match="abstract",
    ):
        Sink()


def test_subclass_without_write_is_abstract() -> None:
    class IncompleteSink(Sink):
        pass

    with pytest.raises(
        TypeError,
        match="abstract",
    ):
        IncompleteSink()


def test_subclass_implementing_write_can_be_instantiated() -> None:
    class TestSink(Sink):
        def write(
            self,
            log: BaseLog,
        ) -> None:
            pass

    sink = TestSink()

    assert isinstance(
        sink,
        Sink,
    )


def test_sink_write_receives_log(
    context: LogContext,
) -> None:
    class TestSink(Sink):
        def __init__(self) -> None:
            self.logs: list[BaseLog] = []

        def write(
            self,
            log: BaseLog,
        ) -> None:
            self.logs.append(log)

    sink = TestSink()

    log = InfoLog(
        message="test message",
        context=context,
    )

    sink.write(log)

    assert sink.logs == [
        log,
    ]

    assert sink.logs[0] is log


def test_write_implementation_can_return_none(
    context: LogContext,
) -> None:
    class TestSink(Sink):
        def write(
            self,
            log: BaseLog,
        ) -> None:
            return None

    sink = TestSink()

    log = InfoLog(
        message="test message",
        context=context,
    )

    result = sink.write(log)

    assert result is None


def test_sink_write_is_marked_abstract() -> None:
    assert (
        getattr(
            Sink.write,
            "__isabstractmethod__",
            False,
        )
        is True
    )