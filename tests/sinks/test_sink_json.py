# tests/sinks/test_json.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from monitaudit.models.base import BaseLog
from monitaudit.sinks.base import Sink
from monitaudit.sinks.json import JsonSink


class FakeLog:
    def __init__(
        self,
        serialised: str,
    ) -> None:
        self.serialised = serialised
        self.calls = 0

    def model_dump_json(
        self,
    ) -> str:
        self.calls += 1
        return self.serialised


class FailingLog:
    def __init__(
        self,
        exception: Exception,
    ) -> None:
        self.exception = exception
        self.calls = 0

    def model_dump_json(
        self,
    ) -> str:
        self.calls += 1
        raise self.exception


def as_base_log(
    value: Any,
) -> BaseLog:
    """
    Cast a test double to BaseLog.

    JsonSink only requires model_dump_json(), so these tests avoid
    coupling sink behaviour to BaseLog model validation.
    """

    return cast(
        BaseLog,
        value,
    )


class TestJsonSinkConstruction:
    def test_inherits_from_sink(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            str(
                tmp_path / "log.jsonl"
            )
        )

        assert isinstance(
            sink,
            Sink,
        )

    def test_stores_path_as_path_object(
        self,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "log.jsonl"

        sink = JsonSink(
            str(path)
        )

        assert sink.path == path
        assert isinstance(
            sink.path,
            Path,
        )

    def test_accepts_relative_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(
            tmp_path
        )

        sink = JsonSink(
            "output/log.jsonl"
        )

        assert sink.path == Path(
            "output/log.jsonl"
        )

    def test_rejects_empty_path(
        self,
    ) -> None:
        with pytest.raises(
            ValueError
        ) as exception_info:
            JsonSink("")

        assert (
            str(exception_info.value)
            == "JSON sink path cannot be empty."
        )

    def test_whitespace_path_is_currently_accepted(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(
            tmp_path
        )

        sink = JsonSink("   ")

        assert sink.path == Path("   ")


class TestDirectoryCreation:
    def test_creates_parent_directory(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "output"
            / "json"
            / "log.jsonl"
        )

        assert not path.parent.exists()

        JsonSink(
            str(path)
        )

        assert path.parent.exists()
        assert path.parent.is_dir()

    def test_creates_nested_parent_directories(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "one"
            / "two"
            / "three"
            / "log.jsonl"
        )

        JsonSink(
            str(path)
        )

        assert path.parent.is_dir()

    def test_existing_parent_directory_is_allowed(
        self,
        tmp_path: Path,
    ) -> None:
        directory = (
            tmp_path
            / "output"
        )

        directory.mkdir()

        path = (
            directory
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        assert sink.path == path

    def test_construction_does_not_create_output_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "output"
            / "log.jsonl"
        )

        JsonSink(
            str(path)
        )

        assert path.parent.exists()
        assert not path.exists()

    def test_directory_creation_error_is_propagated(
        self,
        tmp_path: Path,
    ) -> None:
        parent_file = (
            tmp_path
            / "not-a-directory"
        )

        parent_file.write_text(
            "existing file",
            encoding="utf-8",
        )

        target = (
            parent_file
            / "log.jsonl"
        )

        with pytest.raises(
            OSError
        ):
            JsonSink(
                str(target)
            )


class TestWrite:
    def test_write_creates_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        log = FakeLog(
            '{"message":"hello"}'
        )

        sink.write(
            as_base_log(log)
        )

        assert path.exists()
        assert path.is_file()

    def test_write_calls_model_dump_json_once(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        log = FakeLog(
            '{"message":"hello"}'
        )

        sink.write(
            as_base_log(log)
        )

        assert log.calls == 1

    def test_write_returns_none(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            str(
                tmp_path
                / "log.jsonl"
            )
        )

        log = FakeLog(
            '{"message":"hello"}'
        )

        result = sink.write(
            as_base_log(log)
        )

        assert result is None

    def test_write_writes_exact_serialised_value(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        serialised = (
            '{"message":"hello","level":"INFO"}'
        )

        sink.write(
            as_base_log(
                FakeLog(
                    serialised
                )
            )
        )

        assert path.read_text(
            encoding="utf-8"
        ) == (
            serialised
            + "\n"
        )

    def test_write_adds_newline(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    '{"value":1}'
                )
            )
        )

        content = path.read_text(
            encoding="utf-8"
        )

        assert content.endswith(
            "\n"
        )

    def test_write_does_not_add_extra_blank_line(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    '{"value":1}'
                )
            )
        )

        assert path.read_text(
            encoding="utf-8"
        ) == '{"value":1}\n'


class TestAppendBehaviour:
    def test_multiple_writes_are_appended(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    '{"id":1}'
                )
            )
        )
        sink.write(
            as_base_log(
                FakeLog(
                    '{"id":2}'
                )
            )
        )
        sink.write(
            as_base_log(
                FakeLog(
                    '{"id":3}'
                )
            )
        )

        assert path.read_text(
            encoding="utf-8"
        ) == (
            '{"id":1}\n'
            '{"id":2}\n'
            '{"id":3}\n'
        )

    def test_existing_file_content_is_preserved(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        path.write_text(
            '{"existing":true}\n',
            encoding="utf-8",
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    '{"new":true}'
                )
            )
        )

        assert path.read_text(
            encoding="utf-8"
        ) == (
            '{"existing":true}\n'
            '{"new":true}\n'
        )

    def test_each_write_calls_its_log_once(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            str(
                tmp_path
                / "log.jsonl"
            )
        )

        first = FakeLog(
            '{"id":1}'
        )
        second = FakeLog(
            '{"id":2}'
        )

        sink.write(
            as_base_log(first)
        )
        sink.write(
            as_base_log(second)
        )

        assert first.calls == 1
        assert second.calls == 1


class TestJsonLines:
    def test_each_line_is_valid_json(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    '{"id":1,"message":"first"}'
                )
            )
        )
        sink.write(
            as_base_log(
                FakeLog(
                    '{"id":2,"message":"second"}'
                )
            )
        )

        lines = path.read_text(
            encoding="utf-8"
        ).splitlines()

        assert len(lines) == 2

        assert json.loads(
            lines[0]
        ) == {
            "id": 1,
            "message": "first",
        }

        assert json.loads(
            lines[1]
        ) == {
            "id": 2,
            "message": "second",
        }

    def test_preserves_json_null(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    '{"value":null}'
                )
            )
        )

        line = path.read_text(
            encoding="utf-8"
        ).strip()

        assert json.loads(
            line
        ) == {
            "value": None,
        }

    def test_preserves_nested_json(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        serialised = (
            '{"parameters":{"customer_id":42,'
            '"active":true}}'
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    serialised
                )
            )
        )

        result = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        assert result == {
            "parameters": {
                "customer_id": 42,
                "active": True,
            }
        }


class TestEncoding:
    @pytest.mark.parametrize(
        "message",
        [
            "Hello",
            "München",
            "café",
            "日本語",
            "你好",
            "🙂",
        ],
    )
    def test_utf8_content_can_be_written(
        self,
        tmp_path: Path,
        message: str,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        serialised = json.dumps(
            {
                "message": message,
            },
            ensure_ascii=False,
        )

        sink = JsonSink(
            str(path)
        )

        sink.write(
            as_base_log(
                FakeLog(
                    serialised
                )
            )
        )

        result = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        assert result == {
            "message": message,
        }


class TestSerialisationFailures:
    def test_model_dump_json_error_is_propagated(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        expected_exception = RuntimeError(
            "serialisation failed"
        )

        log = FailingLog(
            expected_exception
        )

        with pytest.raises(
            RuntimeError
        ) as exception_info:
            sink.write(
                as_base_log(log)
            )

        assert (
            exception_info.value
            is expected_exception
        )
        assert log.calls == 1

    def test_serialisation_failure_does_not_write_record(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        log = FailingLog(
            RuntimeError(
                "serialisation failed"
            )
        )

        with pytest.raises(
            RuntimeError
        ):
            sink.write(
                as_base_log(log)
            )

        if path.exists():
            assert path.read_text(
                encoding="utf-8"
            ) == ""


class TestFilesystemFailures:
    def test_write_error_is_propagated(
        self,
        tmp_path: Path,
    ) -> None:
        directory = (
            tmp_path
            / "output"
        )

        sink = JsonSink(
            str(directory)
        )

        directory.mkdir(
            exist_ok=True,
        )

        with pytest.raises(
            OSError
        ):
            sink.write(
                as_base_log(
                    FakeLog(
                        '{"message":"test"}'
                    )
                )
            )


class TestSinkReuse:
    def test_same_sink_can_write_multiple_records(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        for index in range(10):
            sink.write(
                as_base_log(
                    FakeLog(
                        json.dumps(
                            {
                                "index": index,
                            }
                        )
                    )
                )
            )

        lines = path.read_text(
            encoding="utf-8"
        ).splitlines()

        assert len(lines) == 10

        assert [
            json.loads(
                line
            )["index"]
            for line in lines
        ] == list(
            range(10)
        )

    def test_two_sink_instances_can_append_same_file(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        first_sink = JsonSink(
            str(path)
        )
        second_sink = JsonSink(
            str(path)
        )

        first_sink.write(
            as_base_log(
                FakeLog(
                    '{"source":"first"}'
                )
            )
        )

        second_sink.write(
            as_base_log(
                FakeLog(
                    '{"source":"second"}'
                )
            )
        )

        assert path.read_text(
            encoding="utf-8"
        ) == (
            '{"source":"first"}\n'
            '{"source":"second"}\n'
        )


class TestSinkContract:
    def test_json_sink_is_sink_subclass(
        self,
    ) -> None:
        assert issubclass(
            JsonSink,
            Sink,
        )

    def test_write_is_callable(
        self,
        tmp_path: Path,
    ) -> None:
        sink = JsonSink(
            str(
                tmp_path
                / "log.jsonl"
            )
        )

        assert callable(
            sink.write
        )

    def test_path_is_publicly_accessible(
        self,
        tmp_path: Path,
    ) -> None:
        path = (
            tmp_path
            / "log.jsonl"
        )

        sink = JsonSink(
            str(path)
        )

        assert sink.path == path