# tests/sinks/test_memory.py

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink
from monitaudit.sinks.memory import MemorySink


def make_log() -> BaseLog:
    """
    Create a lightweight BaseLog object for MemorySink tests.

    MemorySink does not inspect or validate log fields. It only stores the
    BaseLog instance supplied to write(), so constructing an unvalidated
    model keeps these tests isolated from BaseLog validation behaviour.
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


class TestMemorySinkConstruction:
    def test_constructs_empty_sink(
        self,
    ) -> None:
        sink = MemorySink()

        assert sink.logs == []

    def test_initial_length_is_zero(
        self,
    ) -> None:
        sink = MemorySink()

        assert len(sink) == 0

    def test_logs_is_list(
        self,
    ) -> None:
        sink = MemorySink()

        assert isinstance(
            sink.logs,
            list,
        )

    def test_memory_sink_inherits_from_sink(
        self,
    ) -> None:
        sink = MemorySink()

        assert isinstance(
            sink,
            Sink,
        )

    def test_each_instance_has_independent_log_storage(
        self,
    ) -> None:
        first = MemorySink()
        second = MemorySink()

        assert first.logs is not second.logs

        log = make_log()

        first.write(log)

        assert first.logs == [log]
        assert second.logs == []


class TestWrite:
    def test_write_stores_log(
        self,
    ) -> None:
        sink = MemorySink()
        log = make_log()

        sink.write(log)

        assert sink.logs == [log]

    def test_write_returns_none(
        self,
    ) -> None:
        sink = MemorySink()
        log = make_log()

        result = sink.write(log)

        assert result is None

    def test_write_stores_same_object_reference(
        self,
    ) -> None:
        sink = MemorySink()
        log = make_log()

        sink.write(log)

        assert sink.logs[0] is log

    def test_write_does_not_copy_log(
        self,
    ) -> None:
        sink = MemorySink()
        log = make_log()

        sink.write(log)

        stored = sink.logs[0]

        assert stored is log

    def test_multiple_writes_append_logs(
        self,
    ) -> None:
        sink = MemorySink()

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

    def test_multiple_writes_preserve_insertion_order(
        self,
    ) -> None:
        sink = MemorySink()

        logs = [
            make_log(),
            make_log(),
            make_log(),
            make_log(),
        ]

        for log in logs:
            sink.write(log)

        assert sink.logs == logs

        for actual, expected in zip(
            sink.logs,
            logs,
            strict=True,
        ):
            assert actual is expected

    def test_same_log_can_be_written_multiple_times(
        self,
    ) -> None:
        sink = MemorySink()
        log = make_log()

        sink.write(log)
        sink.write(log)
        sink.write(log)

        assert sink.logs == [
            log,
            log,
            log,
        ]

        assert all(
            stored is log
            for stored in sink.logs
        )

    def test_write_increases_length(
        self,
    ) -> None:
        sink = MemorySink()

        assert len(sink) == 0

        sink.write(make_log())

        assert len(sink) == 1

        sink.write(make_log())

        assert len(sink) == 2

        sink.write(make_log())

        assert len(sink) == 3


class TestLength:
    def test_len_matches_number_of_stored_logs(
        self,
    ) -> None:
        sink = MemorySink()

        logs = [
            make_log(),
            make_log(),
            make_log(),
        ]

        for log in logs:
            sink.write(log)

        assert len(sink) == len(logs)

    @pytest.mark.parametrize(
        "count",
        [
            0,
            1,
            2,
            5,
            10,
            100,
        ],
    )
    def test_len_for_number_of_writes(
        self,
        count: int,
    ) -> None:
        sink = MemorySink()

        for _ in range(count):
            sink.write(
                make_log()
            )

        assert len(sink) == count

    def test_len_reflects_direct_logs_changes(
        self,
    ) -> None:
        sink = MemorySink()

        sink.logs.append(
            make_log()
        )
        sink.logs.append(
            make_log()
        )

        assert len(sink) == 2

    def test_len_returns_int(
        self,
    ) -> None:
        sink = MemorySink()

        assert isinstance(
            len(sink),
            int,
        )


class TestIteration:
    def test_empty_sink_is_iterable(
        self,
    ) -> None:
        sink = MemorySink()

        assert list(sink) == []

    def test_iterates_over_stored_logs(
        self,
    ) -> None:
        sink = MemorySink()

        first = make_log()
        second = make_log()

        sink.write(first)
        sink.write(second)

        assert list(sink) == [
            first,
            second,
        ]

    def test_iteration_preserves_insertion_order(
        self,
    ) -> None:
        sink = MemorySink()

        logs = [
            make_log(),
            make_log(),
            make_log(),
            make_log(),
        ]

        for log in logs:
            sink.write(log)

        result = list(sink)

        assert len(result) == len(logs)

        for actual, expected in zip(
            result,
            logs,
            strict=True,
        ):
            assert actual is expected

    def test_iter_returns_iterator(
        self,
    ) -> None:
        sink = MemorySink()

        iterator = iter(sink)

        assert isinstance(
            iterator,
            Iterator,
        )

    def test_iterator_reads_same_underlying_logs(
        self,
    ) -> None:
        sink = MemorySink()

        first = make_log()
        second = make_log()

        sink.write(first)
        sink.write(second)

        iterator = iter(sink)

        assert next(iterator) is first
        assert next(iterator) is second

        with pytest.raises(
            StopIteration
        ):
            next(iterator)

    def test_sink_can_be_iterated_multiple_times(
        self,
    ) -> None:
        sink = MemorySink()

        logs = [
            make_log(),
            make_log(),
        ]

        for log in logs:
            sink.write(log)

        first_iteration = list(
            sink
        )
        second_iteration = list(
            sink
        )

        assert first_iteration == logs
        assert second_iteration == logs

    def test_iteration_does_not_remove_logs(
        self,
    ) -> None:
        sink = MemorySink()

        logs = [
            make_log(),
            make_log(),
        ]

        for log in logs:
            sink.write(log)

        list(sink)

        assert sink.logs == logs
        assert len(sink) == 2


class TestClear:
    def test_clear_empty_sink(
        self,
    ) -> None:
        sink = MemorySink()

        result = sink.clear()

        assert result is None
        assert sink.logs == []
        assert len(sink) == 0

    def test_clear_removes_stored_logs(
        self,
    ) -> None:
        sink = MemorySink()

        sink.write(
            make_log()
        )
        sink.write(
            make_log()
        )
        sink.write(
            make_log()
        )

        sink.clear()

        assert sink.logs == []
        assert len(sink) == 0

    def test_clear_returns_none(
        self,
    ) -> None:
        sink = MemorySink()

        sink.write(
            make_log()
        )

        result = sink.clear()

        assert result is None

    def test_clear_uses_existing_list(
        self,
    ) -> None:
        sink = MemorySink()

        logs_reference = sink.logs

        sink.write(
            make_log()
        )

        sink.clear()

        assert sink.logs is logs_reference
        assert logs_reference == []

    def test_iteration_after_clear_is_empty(
        self,
    ) -> None:
        sink = MemorySink()

        sink.write(
            make_log()
        )
        sink.write(
            make_log()
        )

        sink.clear()

        assert list(sink) == []

    def test_sink_can_be_reused_after_clear(
        self,
    ) -> None:
        sink = MemorySink()

        original = make_log()

        sink.write(original)
        sink.clear()

        replacement = make_log()

        sink.write(replacement)

        assert len(sink) == 1
        assert sink.logs == [
            replacement,
        ]
        assert sink.logs[0] is replacement

    def test_multiple_clear_calls_are_safe(
        self,
    ) -> None:
        sink = MemorySink()

        sink.write(
            make_log()
        )

        sink.clear()
        sink.clear()
        sink.clear()

        assert sink.logs == []
        assert len(sink) == 0


class TestCombinedBehaviour:
    def test_write_iterate_clear_and_reuse(
        self,
    ) -> None:
        sink = MemorySink()

        first = make_log()
        second = make_log()

        sink.write(first)
        sink.write(second)

        assert len(sink) == 2
        assert list(sink) == [
            first,
            second,
        ]

        sink.clear()

        assert len(sink) == 0
        assert list(sink) == []

        third = make_log()

        sink.write(third)

        assert len(sink) == 1
        assert list(sink) == [
            third,
        ]

    def test_logs_property_matches_iteration(
        self,
    ) -> None:
        sink = MemorySink()

        logs = [
            make_log(),
            make_log(),
            make_log(),
        ]

        for log in logs:
            sink.write(log)

        assert list(sink) == sink.logs

    def test_length_matches_iteration_count(
        self,
    ) -> None:
        sink = MemorySink()

        for _ in range(10):
            sink.write(
                make_log()
            )

        assert len(sink) == len(
            list(sink)
        )

    def test_stored_records_are_not_transformed(
        self,
    ) -> None:
        sink = MemorySink()
        log = make_log()

        sink.write(log)

        stored = next(
            iter(sink)
        )

        assert stored is log


class TestSinkContract:
    def test_memory_sink_is_sink_subclass(
        self,
    ) -> None:
        assert issubclass(
            MemorySink,
            Sink,
        )

    def test_write_method_is_callable(
        self,
    ) -> None:
        sink = MemorySink()

        assert callable(
            sink.write
        )

    def test_clear_method_is_callable(
        self,
    ) -> None:
        sink = MemorySink()

        assert callable(
            sink.clear
        )

    def test_logs_is_publicly_accessible(
        self,
    ) -> None:
        sink = MemorySink()

        assert hasattr(
            sink,
            "logs",
        )

        assert sink.logs == []