# tests/sinks/test_base.py

from __future__ import annotations

import inspect
from typing import cast

import pytest

from monitaudit.models import BaseLog
from monitaudit.sinks.base import Sink


def make_log() -> BaseLog:
    """
    Create a lightweight BaseLog instance.

    The Sink base class does not inspect BaseLog fields, so these tests do not
    depend on BaseLog validation behaviour.
    """

    model_construct = getattr(
        BaseLog,
        "model_construct",
        None,
    )

    if callable(model_construct):
        return cast(
            BaseLog,
            model_construct(),
        )

    construct = getattr(
        BaseLog,
        "construct",
        None,
    )

    if callable(construct):
        return cast(
            BaseLog,
            construct(),
        )

    return cast(
        BaseLog,
        object.__new__(BaseLog),
    )


class ConcreteSink(Sink):
    def __init__(self) -> None:
        self.logs: list[BaseLog] = []

    def write(
        self,
        log: BaseLog,
    ) -> None:
        self.logs.append(log)


class ReturningSink(Sink):
    def write(
        self,
        log: BaseLog,
    ) -> None:
        del log


class MissingWriteSink(Sink):
    pass


class TestSinkAbstractContract:
    def test_sink_is_abstract_class(
        self,
    ) -> None:
        assert inspect.isabstract(
            Sink
        )

    def test_sink_cannot_be_instantiated(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="abstract",
        ):
            Sink()  # type: ignore[abstract]

    def test_write_is_abstract_method(
        self,
    ) -> None:
        assert getattr(
            Sink.write,
            "__isabstractmethod__",
            False,
        ) is True

    def test_write_is_listed_as_abstract_method(
        self,
    ) -> None:
        assert "write" in Sink.__abstractmethods__

    def test_write_is_only_abstract_method(
        self,
    ) -> None:
        assert Sink.__abstractmethods__ == frozenset(
            {
                "write",
            }
        )


class TestIncompleteSubclass:
    def test_subclass_without_write_is_abstract(
        self,
    ) -> None:
        assert inspect.isabstract(
            MissingWriteSink
        )

    def test_subclass_without_write_cannot_be_instantiated(
        self,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="abstract",
        ):
            MissingWriteSink()  # type: ignore[abstract]

    def test_subclass_without_write_inherits_abstract_method(
        self,
    ) -> None:
        assert (
            "write"
            in MissingWriteSink.__abstractmethods__
        )


class TestConcreteSink:
    def test_subclass_with_write_is_not_abstract(
        self,
    ) -> None:
        assert not inspect.isabstract(
            ConcreteSink
        )

    def test_subclass_with_write_can_be_instantiated(
        self,
    ) -> None:
        sink = ConcreteSink()

        assert isinstance(
            sink,
            ConcreteSink,
        )

    def test_concrete_sink_is_sink_instance(
        self,
    ) -> None:
        sink = ConcreteSink()

        assert isinstance(
            sink,
            Sink,
        )

    def test_concrete_sink_is_sink_subclass(
        self,
    ) -> None:
        assert issubclass(
            ConcreteSink,
            Sink,
        )

    def test_write_is_callable(
        self,
    ) -> None:
        sink = ConcreteSink()

        assert callable(
            sink.write
        )

    def test_write_receives_log(
        self,
    ) -> None:
        sink = ConcreteSink()
        log = make_log()

        sink.write(log)

        assert sink.logs == [
            log,
        ]

    def test_write_preserves_log_identity(
        self,
    ) -> None:
        sink = ConcreteSink()
        log = make_log()

        sink.write(log)

        assert sink.logs[0] is log

    def test_write_can_receive_multiple_logs(
        self,
    ) -> None:
        sink = ConcreteSink()

        first = make_log()
        second = make_log()
        third = make_log()

        sink.write(first)
        sink.write(second)
        sink.write(third)

        assert sink.logs == [
            first,
            second,
            third,
        ]

    def test_write_returns_none(
        self,
    ) -> None:
        sink = ConcreteSink()

        result = sink.write(
            make_log()
        )

        assert result is None


class TestSinkWriteSignature:
    def test_write_signature_contains_self_and_log(
        self,
    ) -> None:
        signature = inspect.signature(
            Sink.write
        )

        assert list(
            signature.parameters
        ) == [
            "self",
            "log",
        ]

    def test_log_parameter_is_annotated_as_base_log(
        self,
    ) -> None:
        signature = inspect.signature(
            Sink.write,
            eval_str=True,
        )

        assert (
            signature.parameters[
                "log"
            ].annotation
            is BaseLog
        )

    def test_write_return_annotation_is_none(
        self,
    ) -> None:
        signature = inspect.signature(
            Sink.write,
            eval_str=True,
        )

        assert (
            signature.return_annotation
            is None
        )


class TestMultipleImplementations:
    def test_multiple_concrete_implementations_are_supported(
        self,
    ) -> None:
        first = ConcreteSink()
        second = ReturningSink()

        assert isinstance(
            first,
            Sink,
        )
        assert isinstance(
            second,
            Sink,
        )

    def test_alternative_write_implementation_can_be_called(
        self,
    ) -> None:
        sink = ReturningSink()

        result = sink.write(
            make_log()
        )

        assert result is None


class TestAbstractWriteBody:
    def test_base_write_can_be_called_explicitly_from_subclass(
        self,
    ) -> None:
        """
        The abstract method currently has a no-op body (`pass`).

        Abstract methods remain callable explicitly through the base class.
        This test locks down that current behaviour.
        """

        sink = ConcreteSink()
        log = make_log()

        result = Sink.write(
            sink,
            log,
        )

        assert result is None

    def test_explicit_base_write_does_not_call_subclass_write(
        self,
    ) -> None:
        sink = ConcreteSink()
        log = make_log()

        Sink.write(
            sink,
            log,
        )

        assert sink.logs == []