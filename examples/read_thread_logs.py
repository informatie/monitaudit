from __future__ import annotations

from pyspark.sql import SparkSession


# ---------------------------------------------------------------------------
# Query index
# ---------------------------------------------------------------------------
#
# Query 01: Show all log records chronologically to inspect parallel execution.
# Query 02: List distinct worker threads actually used by the executor.
# Query 03: Group logs by thread and workspace to inspect worker assignment.
# Query 04: Show detailed thread/workspace records for execution debugging.
# Query 05: Count logs by thread, workspace, function and trace event.
# Query 06: Count trace lifecycle events by workspace and traced function.
# Query 07: Compare starts, ends and errors to validate trace lifecycle health.
# Query 08: Find invalid element-to-workspace parent_call_id relationships.
# Query 09: Show every element/workspace parent relationship with OK/INVALID.
# Query 10: Show the root call_id assigned to every workspace trace.
# Query 11: Detect root call_id reuse across different workspace traces.
# Query 12: Summarise workspace and logging activity for each executor thread.
# ---------------------------------------------------------------------------


LOG_PATH = (
    "logs/examples/"
    "main_workspace_thread_executor.jsonl"
)


spark = (
    SparkSession.builder
    .appName("monitauditLogAnalysis")
    .master("local[*]")
    .getOrCreate()
)


logs = spark.read.json(
    LOG_PATH
)

logs.createOrReplaceTempView(
    "monitaudit_logs"
)


# ---------------------------------------------------------------------------
# Query 01: Complete chronological log
#
# Purpose
# -------
# Display the complete monitaudit log in timestamp order.
#
# Goal
# ----
# Provide a general overview of the parallel execution and show how records
# from different workers are interleaved.
#
# What to look for
# ----------------
# - Workspace and element processing may be interleaved.
# - thread_name/thread_id identify worker activity when present.
# - function identifies process_workspace or process_element.
# - call_id identifies the current traced function invocation.
# - parent_call_id identifies the parent trace.
# - event shows function_start/function_end/function_error when applicable.
# - A successful example should not contain unexpected function_error events.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        timestamp,
        level,
        function,
        call_id,
        parent_call_id,
        attributes.ws_nummer AS ws_nummer,
        attributes.element_code AS element_code,
        attributes.thread_name AS thread_name,
        attributes.thread_id AS thread_id,
        attributes.event AS event,
        message
    FROM monitaudit_logs
    ORDER BY timestamp
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 02: Worker threads used
#
# Purpose
# -------
# Display the distinct executor workers that appear in the log.
#
# Goal
# ----
# Verify which ThreadPoolExecutor workers actually executed application work.
#
# What to look for
# ----------------
# With thread_name_prefix="workspace-worker", names may look like:
#
#   workspace-worker_0
#   workspace-worker_1
#   workspace-worker_2
#
# max_workers=3 permits three workers. Thread scheduling determines which
# workers actually receive work.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT DISTINCT
        attributes.thread_name AS thread_name,
        attributes.thread_id AS thread_id
    FROM monitaudit_logs
    WHERE attributes.thread_name IS NOT NULL
    ORDER BY thread_name
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 03: Thread-to-workspace distribution
#
# Purpose
# -------
# Group logging activity by worker thread and workspace.
#
# Goal
# ----
# Show which workers handled which workspaces and over what observed period.
#
# What to look for
# ----------------
# - thread_name identifies the executor worker.
# - thread_id identifies the Python thread.
# - ws_nummer identifies the workspace.
# - log_count gives the amount of logging for that combination.
# - first_log/last_log show its observed logging interval.
#
# A workspace submitted as one executor task should normally remain associated
# with its worker during that task.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        attributes.thread_name AS thread_name,
        attributes.thread_id AS thread_id,

        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ) AS ws_nummer,

        COUNT(*) AS log_count,
        MIN(timestamp) AS first_log,
        MAX(timestamp) AS last_log

    FROM monitaudit_logs

    WHERE
        attributes.thread_name IS NOT NULL

        AND COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ) IS NOT NULL

    GROUP BY
        attributes.thread_name,
        attributes.thread_id,

        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        )

    ORDER BY
        thread_name,
        ws_nummer
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 04: Detailed thread/workspace debugging
#
# Purpose
# -------
# Show detailed log records grouped logically by thread and workspace.
#
# Goal
# ----
# Make it easier to inspect execution and trace relationships within each
# workspace.
#
# What to look for
# ----------------
# - Workspace records should contain the expected ws_nummer.
# - Element records should belong to that workspace.
# - Each traced element has its own call_id.
# - Element parent_call_id should point to the workspace call_id.
# - Timestamps show execution order within each worker.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        attributes.thread_name AS thread_name,

        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ) AS ws_nummer,

        timestamp,
        function,
        attributes.event AS event,
        parameters.element_code AS element_code,
        call_id,
        parent_call_id,
        message

    FROM monitaudit_logs

    WHERE
        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ) IS NOT NULL

    ORDER BY
        thread_name,
        ws_nummer,
        timestamp
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 05: Counts by thread, workspace, function and event
#
# Purpose
# -------
# Aggregate log activity by thread, workspace, function and trace event.
#
# Goal
# ----
# Show how many records each function/event combination generated.
#
# What to look for
# ----------------
# Trace lifecycle records can contain:
#
#   function_start
#   function_end
#   function_error
#
# Records without a trace event are grouped under "log".
#
# Successful traced invocations should have matching START and END records.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        attributes.thread_name AS thread_name,
        attributes.thread_id AS thread_id,

        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ) AS ws_nummer,

        function,

        COALESCE(
            attributes.event,
            'log'
        ) AS event,

        COUNT(*) AS log_count,
        MIN(timestamp) AS first_log,
        MAX(timestamp) AS last_log

    FROM monitaudit_logs

    WHERE
        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ) IS NOT NULL

    GROUP BY
        attributes.thread_name,
        attributes.thread_id,

        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ),

        function,

        COALESCE(
            attributes.event,
            'log'
        )

    ORDER BY
        thread_name,
        ws_nummer,
        function,
        event
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 06: Trace lifecycle counts
#
# Purpose
# -------
# Count only START, END and ERROR trace lifecycle records.
#
# Goal
# ----
# Provide a compact overview of trace activity for each workspace/function.
#
# What to look for
# ----------------
# For successful executions:
#
#   function_start count == function_end count
#
# and:
#
#   function_error count == 0
#
# process_workspace normally has one START and one END per workspace.
# process_element normally has one START and one END per element.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ) AS ws_nummer,

        function,
        attributes.event AS event,

        COUNT(*) AS event_count

    FROM monitaudit_logs

    WHERE
        attributes.event IN (
            'function_start',
            'function_end',
            'function_error'
        )

    GROUP BY
        COALESCE(
            attributes.ws_nummer,
            parameters.ws_nummer
        ),

        function,
        attributes.event

    ORDER BY
        ws_nummer,
        function,
        event
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 07: Trace-health summary
#
# Purpose
# -------
# Count START, END and ERROR events in one row per workspace and function.
#
# Goal
# ----
# Detect missing terminal trace events or unexpected failures.
#
# What to look for
# ----------------
# For successful traces:
#
#   starts == ends
#   errors == 0
#
# More generally:
#
#   starts == ends + errors
#
# Warning signs:
#
#   starts > ends + errors
#       A trace appears to have no terminal event.
#
#   errors > 0
#       One or more traced calls failed.
#
#   starts < ends + errors
#       More terminal events exist than recorded START events.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        COALESCE(
            parameters.ws_nummer,
            attributes.ws_nummer
        ) AS ws_nummer,

        function,

        SUM(
            CASE
                WHEN attributes.event = 'function_start'
                THEN 1
                ELSE 0
            END
        ) AS starts,

        SUM(
            CASE
                WHEN attributes.event = 'function_end'
                THEN 1
                ELSE 0
            END
        ) AS ends,

        SUM(
            CASE
                WHEN attributes.event = 'function_error'
                THEN 1
                ELSE 0
            END
        ) AS errors

    FROM monitaudit_logs

    WHERE
        function IN (
            'process_workspace',
            'process_element'
        )

        AND attributes.event IN (
            'function_start',
            'function_end',
            'function_error'
        )

    GROUP BY
        COALESCE(
            parameters.ws_nummer,
            attributes.ws_nummer
        ),
        function

    ORDER BY
        ws_nummer,
        function
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 08: Broken parent_call_id relationships
#
# Purpose
# -------
# Find element traces whose parent_call_id does not match their workspace.
#
# Goal
# ----
# Automatically verify:
#
#   process_element.parent_call_id
#       ==
#   process_workspace.call_id
#
# What to look for
# ----------------
# EXPECTED RESULT: ZERO ROWS.
#
# Zero rows means all element traces are attached to the expected workspace.
#
# Any returned row is a broken relationship. Inspect:
#
#   ws_nummer
#   element_code
#   element_call_id
#   parent_call_id
#   workspace_call_id
#
# This is especially important when workspaces execute concurrently.
# ---------------------------------------------------------------------------

spark.sql(
    """
    WITH workspace_calls AS (
        SELECT
            parameters.ws_nummer AS ws_nummer,
            call_id AS workspace_call_id

        FROM monitaudit_logs

        WHERE
            function = 'process_workspace'
            AND attributes.event = 'function_start'
    ),

    element_calls AS (
        SELECT
            parameters.ws_nummer AS ws_nummer,
            parameters.element_code AS element_code,
            call_id AS element_call_id,
            parent_call_id

        FROM monitaudit_logs

        WHERE
            function = 'process_element'
            AND attributes.event = 'function_start'
    )

    SELECT
        element.ws_nummer,
        element.element_code,
        element.element_call_id,
        element.parent_call_id,
        workspace.workspace_call_id

    FROM element_calls AS element

    INNER JOIN workspace_calls AS workspace
        ON element.ws_nummer = workspace.ws_nummer

    WHERE
        element.parent_call_id
        <> workspace.workspace_call_id

    ORDER BY
        element.ws_nummer,
        element.element_code
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 09: Element-to-workspace hierarchy
#
# Purpose
# -------
# Display every element START together with its expected workspace parent.
#
# Goal
# ----
# Positively demonstrate the parent_call_id relationship rather than only
# reporting broken relationships.
#
# What to look for
# ----------------
# parent_relationship should be:
#
#   OK
#
# on every row.
#
# Within one workspace:
# - workspace_call_id should remain constant.
# - every element_call_id should be unique.
# - element_parent_call_id should equal workspace_call_id.
#
# Across different workspaces:
# - workspace_call_id should differ.
# ---------------------------------------------------------------------------

spark.sql(
    """
    WITH workspace_calls AS (
        SELECT
            parameters.ws_nummer AS ws_nummer,
            call_id AS workspace_call_id

        FROM monitaudit_logs

        WHERE
            function = 'process_workspace'
            AND attributes.event = 'function_start'
    ),

    element_calls AS (
        SELECT
            parameters.ws_nummer AS ws_nummer,
            parameters.element_code AS element_code,
            call_id AS element_call_id,
            parent_call_id AS element_parent_call_id

        FROM monitaudit_logs

        WHERE
            function = 'process_element'
            AND attributes.event = 'function_start'
    )

    SELECT
        element.ws_nummer,
        element.element_code,
        workspace.workspace_call_id,
        element.element_call_id,
        element.element_parent_call_id,

        CASE
            WHEN element.element_parent_call_id
                 = workspace.workspace_call_id
            THEN 'OK'
            ELSE 'INVALID'
        END AS parent_relationship

    FROM element_calls AS element

    INNER JOIN workspace_calls AS workspace
        ON element.ws_nummer = workspace.ws_nummer

    ORDER BY
        element.ws_nummer,
        element.element_code
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 10: Workspace root call IDs
#
# Purpose
# -------
# Show the root call_id assigned to every process_workspace invocation.
#
# Goal
# ----
# Verify that concurrently executing workspace traces remain independent.
#
# What to look for
# ----------------
# Conceptually:
#
#   Workspace 301 -> UUID-A
#   Workspace 302 -> UUID-B
#   Workspace 303 -> UUID-C
#
# Each workspace invocation should have its own call_id.
#
# Because process_workspace is the root traced operation in each worker,
# its parent_call_id should normally be NULL.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        parameters.ws_nummer AS ws_nummer,
        call_id AS workspace_call_id,
        parent_call_id

    FROM monitaudit_logs

    WHERE
        function = 'process_workspace'
        AND attributes.event = 'function_start'

    ORDER BY
        ws_nummer
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 11: Detect workspace call_id reuse
#
# Purpose
# -------
# Find a workspace call_id associated with multiple distinct workspaces.
#
# Goal
# ----
# Detect accidental trace identity reuse across concurrent workspace calls.
#
# What to look for
# ----------------
# EXPECTED RESULT: ZERO ROWS.
#
# Any returned row means the same workspace_call_id occurs for more than one
# distinct ws_nummer and should be investigated.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        call_id AS workspace_call_id,

        COUNT(
            DISTINCT parameters.ws_nummer
        ) AS workspace_count

    FROM monitaudit_logs

    WHERE
        function = 'process_workspace'
        AND attributes.event = 'function_start'

    GROUP BY
        call_id

    HAVING
        COUNT(
            DISTINCT parameters.ws_nummer
        ) > 1

    ORDER BY
        workspace_call_id
    """
).show(
    200,
    truncate=False,
)


# ---------------------------------------------------------------------------
# Query 12: Thread/workspace execution matrix
#
# Purpose
# -------
# Summarise workspace and logging activity by worker thread.
#
# Goal
# ----
# Provide a compact overview of how work was distributed across the executor.
#
# What to look for
# ----------------
# - thread_name identifies the worker.
# - workspace_count shows distinct workspaces observed on that worker.
# - log_count shows how many matching log records the worker produced.
#
# With three submitted workspaces and max_workers=3, this shows how the work
# was actually distributed without assuming a fixed scheduler assignment.
# ---------------------------------------------------------------------------

spark.sql(
    """
    SELECT
        attributes.thread_name AS thread_name,
        attributes.thread_id AS thread_id,

        COUNT(
            DISTINCT COALESCE(
                attributes.ws_nummer,
                parameters.ws_nummer
            )
        ) AS workspace_count,

        COUNT(*) AS log_count

    FROM monitaudit_logs

    WHERE
        attributes.thread_name IS NOT NULL

    GROUP BY
        attributes.thread_name,
        attributes.thread_id

    ORDER BY
        thread_name
    """
).show(
    200,
    truncate=False,
)


spark.stop()