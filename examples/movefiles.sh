#!/usr/bin/env bash

set -euo pipefail

# Run this script from the examples/ directory.
#
# Creates:
#
# examples/
# ├── basic/
# ├── configuration/
# ├── sinks/
# ├── errors/
# ├── redaction/
# ├── sink_failure/
# └── threading/

move_file() {
    source_file="$1"
    target_directory="$2"

    if [ ! -e "$source_file" ]; then
        echo "SKIP    $source_file (not found)"
        return
    fi

    if [ -e "$target_directory/$source_file" ]; then
        echo "ERROR   $target_directory/$source_file already exists"
        exit 1
    fi

    mv "$source_file" "$target_directory/"
    echo "MOVE    $source_file -> $target_directory/"
}


echo "Creating example directories..."

mkdir -p \
    basic \
    configuration \
    sinks \
    errors \
    redaction \
    sink_failure \
    threading


echo
echo "Moving basic examples..."

move_file main_basic.py basic
move_file main_demo.py basic
move_file main_all.py basic
move_file main_trace.py basic
move_file main_parameter.py basic
move_file main_parameter_limit.py basic


echo
echo "Moving configuration examples..."

move_file main_read_setting.py configuration


echo
echo "Moving sink examples..."

move_file main_console_sink.py sinks
move_file main_file_sink.py sinks
move_file main_json_sink.py sinks
move_file main_all_sinks.py sinks
move_file main_delta_local.py sinks
move_file main_delta_databricks.py sinks
move_file main_query_delta.py sinks


echo
echo "Moving error examples..."

move_file main_errors.py errors
move_file main_errors_workspace.py errors
move_file main_stacktrace.py errors
move_file main_nested_error_handled.py errors
move_file main_nested_error_parameter.py errors
move_file main_nested_error_serialized.py errors
move_file main_nested_error_json_safe.py errors
move_file main_nested_workspace_failure.py errors


echo
echo "Moving redaction and serialisation examples..."

move_file main_redaction.py redaction
move_file main_redaction_exact_names.py redaction
move_file main_redaction_suffixes.py redaction
move_file main_json_safe_types.py redaction


echo
echo "Moving sink failure examples..."

move_file main_sink_failure_continue.py sink_failure
move_file main_sink_failure_raise.py sink_failure


echo
echo "Moving threading examples..."

move_file main_thread_executor.py threading
move_file main_thread_failure.py threading
move_file main_thread_trace_isolation.py threading
move_file main_many_thread_tasks.py threading
move_file main_element_thread_executor.py threading
move_file main_workspace_thread_executor.py threading
move_file read_thread_logs.py threading


echo
echo "Done."
echo
echo "Files intentionally left in examples/:"
echo "  config/"
echo "  data/"
echo "  howto_run.txt"
echo
echo "NOTE: Review imports, file paths and documentation that reference"
echo "the previous example locations."