# monitaudit 🔍 🛡️

A lightweight Python framework for structured logging, application monitoring, tracing, system auditing, and event tracking.

`monitaudit` provides a clear, developer-friendly interface for application telemetry, structured debugging logs, tracing, and audit events.

It is designed to make observability and auditing explicit while keeping monitoring and logging concerns separated from application logic.

## Key Highlights

- **Structured Logging**  
  Capture consistent, structured application events that can be processed, queried, and analysed.

- **Tracing**  
  Track application execution flows and operations using an explicit tracing interface.

- **Application Monitoring**  
  Observe runtime behaviour through configurable logging and monitoring components.

- **Audit Tracking**  
  Record important application actions, events, and state changes for operational and audit purposes.

- **Configurable Sinks**  
  Route log and audit events to configured output destinations.

- **Modern Python**  
  Designed around type annotations, explicit APIs, and modern Python development practices.

## Installation

Install `monitaudit` from PyPI using `uv`:

```bash
uv add monitaudit
```

Or using `pip`:

```bash
pip install monitaudit
```

## Local Development

When developing `monitaudit` and another application on the same machine, use an editable local installation:

```bash
uv add --editable /home/zadmin/projects/monitaudit
```

This allows the consuming application to use your local `monitaudit` source during development without publishing a new package release.

## Examples

Complete examples, configuration files, sink examples, and usage patterns are maintained in the dedicated examples repository:

👉 **[monitaudit-examples](https://github.com/informatie/monitaudit-examples)**

The examples repository is the recommended starting point for learning how to configure and integrate `monitaudit` into an application.

---

## Configuration

Monitaudit uses a `config` directory containing two configuration files:

```text
your-application/
├── config/
│   ├── monitaudit.properties
│   └── monitaudit.runtime
└── main.py
```

### `monitaudit.properties`

`monitaudit.properties` contains the default Monitaudit configuration.

These values define the library defaults and normally do not need to be changed for each runtime environment.

Example:

```properties
# config/monitaudit.properties

[monitaudit]
logging.level=INFO
logging.timer=true
logging.parameters=true
logging.max_parameter_length=1000
logging.sink_failure_mode=continue
```

### `monitaudit.runtime`

`monitaudit.runtime` contains application-specific and environment-specific runtime configuration.

Example:

```yaml
# config/monitaudit.runtime

monitaudit:
  application: my-application

  environments:
    dev:
      logging:
        level: DEBUG

    test:
      logging:
        level: INFO

    prod:
      logging:
        level: INFO
```

The runtime environment can be selected using one of the supported environment variables:

```bash
export MONITAUDIT_ENVIRONMENT=dev
```

or:

```bash
export MONITAUDIT_ENV=dev
```

or:

```bash
export ENV=dev
```

For example:

```bash
MONITAUDIT_ENV=dev uv run python main.py
```

## Example 1: Minimal Usage

```python
import monitaudit


mta = monitaudit.monitaudit_init()

mta.info("Hello from Monitaudit")
```

## Example 2: Basic Logging

```python
import monitaudit


mta = monitaudit.monitaudit_init()

mta.info("Application started")
mta.debug("Processing data")
mta.warning("Example warning")
mta.error("Example error")
```

## Example 3: Application Usage

```python
import monitaudit


mta = monitaudit.monitaudit_init()


def main() -> None:
    mta.info("Application started")

    try:
        mta.info("Processing data")
    except Exception:
        mta.exception("Application failed")
        raise

    mta.info("Application completed")


if __name__ == "__main__":
    main()
```

## More Examples

Complete examples, configuration files, sink examples, and more advanced usage patterns are available in the dedicated examples repository:

👉 **[monitaudit-examples](https://github.com/informatie/monitaudit-examples)**

The examples repository is the recommended starting point for advanced Monitaudit configuration, sinks, tracing, and integration examples.

---

# Complete Configuration Examples

The following examples show the complete Monitaudit configuration files.

## `config/monitaudit.properties`

````properties
# config/monitaudit.properties
#
# ==============================================================================
# MonitAudit - Default Library Configuration
# ==============================================================================
#
# This file contains the default configuration used by MonitAudit.
#
# Application-specific and environment-specific settings should normally be
# placed in:
#
#     config/monitaudit.runtime
#
# The runtime configuration can override defaults defined here.
#
# Recommended project structure:
#
#     your-application/
#     |
#     +-- config/
#     |   +-- monitaudit.properties
#     |   +-- monitaudit.runtime
#     |
#     +-- main.py
#
# Typical application initialisation:
#
#     import monitaudit
#
#     mta = monitaudit.monitaudit_init()
#
#     mta.info("Application started")
#
# ==============================================================================
# LOGGING
# ==============================================================================
#
# Default logging configuration.
#
# level
# -----
# Minimum logging level.
#
# Typical values:
#
#     DEBUG
#     INFO
#     WARNING
#     ERROR
#     CRITICAL
#
# Example:
#
#     logging.level=DEBUG
#
# For normal operation INFO is generally a suitable default.
#
# ------------------------------------------------------------------------------
#
# timer
# -----
# Controls timing information produced by MonitAudit tracing/instrumentation.
#
# Example:
#
#     logging.timer=true
#
# ------------------------------------------------------------------------------
#
# parameters
# ----------
# Controls whether parameters may be included in structured logging/tracing
# information.
#
# Example:
#
#     logging.parameters=true
#
# Do not assume that enabling this option makes arbitrary application data safe
# to log. Applications should still avoid passing secrets, credentials, tokens,
# passwords, or other sensitive information to logging calls.
#
# ------------------------------------------------------------------------------
#
# max_parameter_length
# --------------------
# Maximum length used when recording parameter values.
#
# Long values may be truncated according to MonitAudit's parameter handling.
#
# Example:
#
#     logging.max_parameter_length=1000
#
# ------------------------------------------------------------------------------
#
# sink_failure_mode
# -----------------
# Determines the configured policy for sink failures.
#
# Example:
#
#     logging.sink_failure_mode=continue
#
# The exact values accepted by the installed MonitAudit version should match the
# configuration model used by that release.
#
# ------------------------------------------------------------------------------
#
# file_cycle
# -----------------
# How long
#
# Example:
#
#     logging.sink_failure_mode=continue
#
# The exact values accepted by the installed MonitAudit version should match the
# configuration model used by that release.
#
# ==============================================================================

logging.level=INFO
logging.timer=true
logging.parameters=true
logging.max_parameter_length=1000
logging.sink_failure_mode=continue
logging.file_cycle=10


# ==============================================================================
# SINK CONFIGURATION
# ==============================================================================
#
# A sink determines where MonitAudit events are written.
#
# MonitAudit applications can configure output destinations such as:
#
#     Console
#     File
#     JSON
#     Delta
#
# Sink-specific runtime paths, table names, and environment-dependent settings
# are better placed in monitaudit.runtime when they differ between
# applications or environments.
#
# The examples below illustrate the intended configuration categories.
# Keep the actual property names aligned with the configuration models of the
# MonitAudit release being used.
# ==============================================================================


# ==============================================================================
# CONSOLE SINK
# ==============================================================================
#
# The console sink writes logging output to the application's console.
#
# Typical use:
#
#     Local development
#     Interactive execution
#     Containers
#     CI/CD diagnostics
#
# Example:
#
#     console_sink.enabled=true
#
# ==============================================================================

console_sink.enabled=false


# ==============================================================================
# FILE SINK
# ==============================================================================
#
# The file sink writes MonitAudit events to a text-based log file.
#
# Example runtime configuration:
#
#     file_sink:
#       enabled: true
#       path: output/file_sink/application.log
#
# Paths are application-specific, so the actual output path should preferably
# be configured in monitaudit.runtime rather than hard-coded into the
# library defaults.
#
# ==============================================================================

file_sink.enabled=false


# ==============================================================================
# JSON SINK
# ==============================================================================
#
# The JSON sink writes structured events in JSON format.
#
# This is useful when log output will subsequently be ingested or processed by
# another system.
#
# Example runtime configuration:
#
#     json_sink:
#       enabled: true
#       path: output/json_sink/application.jsonl
#
# Keep application-specific paths in monitaudit.runtime.
#
# ==============================================================================

json_sink.enabled=false


# ==============================================================================
# DELTA SINK
# ==============================================================================
#
# The Delta sink stores structured MonitAudit events in a Delta destination.
#
# From the MonitAudit configuration design, both the logical table and physical
# path belong in configuration rather than being hard-coded in Python.
#
# Example runtime configuration:
#
#     delta_sink:
#       enabled: true
#       table: main.logging.application
#       path: output/delta_sink/application
#
# Table and path values are application/environment-specific and should
# therefore normally be defined in monitaudit.runtime.
#
# ==============================================================================

delta_sink.enabled=false


# ==============================================================================
# EXAMPLE: DEVELOPMENT CONFIGURATION
# ==============================================================================
#
# The properties in this file establish defaults.
#
# A development application could override them from
# monitaudit.runtime, for example:
#
#     monitaudit:
#       application: example-application
#
#       logging:
#         level: INFO
#         timer: true
#         parameters: true
#         max_parameter_length: 1000
#         sink_failure_mode: continue
#
#       sinks:
#         console_sink:
#           enabled: false
#
#         json_sink:
#           enabled: false
#
#         file_sink:
#           enabled: false
#
#         delta_sink:
#           enabled: false
#
# ==============================================================================
# ENVIRONMENT SELECTION
# ==============================================================================
#
# Runtime environment selection is handled outside this properties file.
#
# MonitAudit applications may select their runtime environment using:
#
#     MONITAUDIT_ENVIRONMENT
#     MONITAUDIT_ENV
#     ENV
#
# Example:
#
#     MONITAUDIT_ENV=dev uv run python main.py
#
# Environment-specific configuration belongs in monitaudit.runtime.
#
# ==============================================================================
# RECOMMENDED RESPONSIBILITY SPLIT
# ==============================================================================
#
# monitaudit.properties
# ---------------------
#
#     MonitAudit defaults
#     Logging defaults
#     Default feature behaviour
#     Default sink enablement
#
#
# monitaudit.runtime
# -----------------------
#
#     Application name
#     Environment-specific overrides
#     Output paths
#     Delta table names
#     Application sink configuration
#     Deployment-specific configuration
#
#
# Python application
# ------------------
#
#     import monitaudit
#
#     mta = monitaudit.monitaudit_init()
#
#     mta.info("Application started")
#
# Keeping these responsibilities separate prevents application-specific
# configuration from becoming part of the MonitAudit library defaults.
# ==============================================================================
````

## `config/monitaudit.runtime`

````yaml
# config/monitaudit.yaml
#
# ==============================================================================
# MonitAudit - Runtime Configuration
# ==============================================================================
#
# This file contains application-specific MonitAudit configuration.
#
# MonitAudit configuration is split into:
#
#   monitaudit.properties
#       Library defaults.
#
#   monitaudit.yaml
#       Application/runtime configuration and overrides.
#
# Recommended project structure:
#
#   your-application/
#   |
#   +-- config/
#   |   +-- monitaudit.properties
#   |   +-- monitaudit.yaml
#   |
#   +-- main.py
#
# Typical application initialisation:
#
#   import monitaudit
#
#   mta = monitaudit.monitaudit_init()
#
#   mta.info("Application started")
#
# ==============================================================================

monitaudit:

  # ============================================================================
  # APPLICATION
  # ============================================================================
  #
  # Logical name of the application producing MonitAudit events.
  #
  # Choose a stable name that identifies the application rather than the
  # individual server or process running it.
  #
  # Examples:
  #
  #   customer-api
  #   data-ingestion
  #   billing-service
  #   monitaudit-example
  #
  # ============================================================================

  application: my-application


  # ============================================================================
  # LOGGING
  # ============================================================================
  #
  # Application logging and tracing behaviour.
  #
  # Values specified here override the corresponding MonitAudit defaults.
  #
  # ============================================================================

  logging:

    # --------------------------------------------------------------------------
    # level
    # --------------------------------------------------------------------------
    #
    # Minimum logging level.
    #
    # Common values:
    #
    #   DEBUG
    #   INFO
    #   WARNING
    #   ERROR
    #   CRITICAL
    #
    # DEBUG is useful during development.
    # INFO is recommended as a normal application starting point.
    #
    # --------------------------------------------------------------------------

    level: INFO


    # --------------------------------------------------------------------------
    # timer
    # --------------------------------------------------------------------------
    #
    # Enables timing information for supported tracing/instrumentation.
    #
    # Example:
    #
    #   timer: true
    #
    # --------------------------------------------------------------------------

    timer: true


    # --------------------------------------------------------------------------
    # parameters
    # --------------------------------------------------------------------------
    #
    # Controls whether supported tracing/logging operations can include
    # parameter information.
    #
    # Applications should still avoid logging passwords, authentication
    # credentials, tokens, secrets, or other sensitive information.
    #
    # --------------------------------------------------------------------------

    parameters: true


    # --------------------------------------------------------------------------
    # max_parameter_length
    # --------------------------------------------------------------------------
    #
    # Maximum configured length for logged parameter values.
    #
    # Example:
    #
    #   max_parameter_length: 1000
    #
    # --------------------------------------------------------------------------

    max_parameter_length: 1000


    # --------------------------------------------------------------------------
    # sink_failure_mode
    # --------------------------------------------------------------------------
    #
    # Defines the configured behaviour when an output sink fails.
    #
    # The "continue" mode allows the application to continue processing when
    # supported by the installed MonitAudit version.
    #
    # --------------------------------------------------------------------------

    sink_failure_mode: continue


  # ============================================================================
  # SINKS
  # ============================================================================
  #
  # Sinks determine where MonitAudit events are written.
  #
  # Individual sinks can be enabled or disabled independently.
  #
  # This complete example contains:
  #
  #   console_sink
  #   file_sink
  #   json_sink
  #   delta_sink
  #
  # ============================================================================

  sinks:

    # ==========================================================================
    # CONSOLE SINK
    # ==========================================================================
    #
    # Writes MonitAudit output to the console.
    #
    # Useful for:
    #
    #   - local development
    #   - interactive execution
    #   - containers
    #   - CI/CD diagnostics
    #
    # ==========================================================================

    console_sink:
      enabled: true


    # ==========================================================================
    # FILE SINK
    # ==========================================================================
    #
    # Writes MonitAudit events to a text log file.
    #
    # Relative paths should be interpreted consistently by the application and
    # MonitAudit configuration loader.
    #
    # Example destination:
    #
    #   output/file_sink/application.log
    #
    # Set enabled to false when the file sink is not required.
    #
    # ==========================================================================

    file_sink:
      enabled: false
      path: output/file_sink/application.log


    # ==========================================================================
    # JSON SINK
    # ==========================================================================
    #
    # Writes structured MonitAudit events to JSON output.
    #
    # A .jsonl extension can be used when each log event is stored as an
    # individual JSON record on a separate line.
    #
    # Example destination:
    #
    #   output/json_sink/application.jsonl
    #
    # ==========================================================================

    json_sink:
      enabled: false
      path: output/json_sink/application.jsonl


    # ==========================================================================
    # DELTA SINK
    # ==========================================================================
    #
    # Writes structured events to the configured Delta destination.
    #
    # Both the logical table name and physical path are configuration values.
    # They should not need to be hard-coded in the application.
    #
    # Local example:
    #
    #   table: main.logging.application
    #   path: output/delta_sink/application
    #
    # Set enabled to false when Delta output is not required.
    #
    # ==========================================================================

    delta_sink:
      enabled: false
      table: main.logging.application
      path: output/delta_sink/application


# ==============================================================================
# EXAMPLE CONFIGURATIONS
# ==============================================================================
#
# The examples below are documentation only.
#
# Do not uncomment all examples at the same time if they duplicate the active
# configuration above.
#
#
# ------------------------------------------------------------------------------
# CONSOLE-ONLY APPLICATION
# ------------------------------------------------------------------------------
#
# monitaudit:
#   application: my-console-application
#
#   logging:
#     level: DEBUG
#     timer: true
#     parameters: true
#     max_parameter_length: 1000
#     sink_failure_mode: continue
#
#   sinks:
#     console_sink:
#       enabled: true
#
#
# ------------------------------------------------------------------------------
# FILE LOGGING APPLICATION
# ------------------------------------------------------------------------------
#
# monitaudit:
#   application: my-file-application
#
#   logging:
#     level: INFO
#     timer: true
#     parameters: true
#     max_parameter_length: 1000
#     sink_failure_mode: continue
#
#   sinks:
#     console_sink:
#       enabled: true
#
#     file_sink:
#       enabled: true
#       path: output/file_sink/application.log
#
#
# ------------------------------------------------------------------------------
# JSON LOGGING APPLICATION
# ------------------------------------------------------------------------------
#
# monitaudit:
#   application: my-json-application
#
#   logging:
#     level: INFO
#     timer: true
#     parameters: true
#     max_parameter_length: 1000
#     sink_failure_mode: continue
#
#   sinks:
#     console_sink:
#       enabled: true
#
#     json_sink:
#       enabled: true
#       path: output/json_sink/application.jsonl
#
#
# ------------------------------------------------------------------------------
# ALL SINKS
# ------------------------------------------------------------------------------
#
# monitaudit:
#   application: my-application
#
#   logging:
#     level: DEBUG
#     timer: true
#     parameters: true
#     max_parameter_length: 1000
#     sink_failure_mode: continue
#
#   sinks:
#     console_sink:
#       enabled: true
#
#     file_sink:
#       enabled: true
#       path: output/file_sink/application.log
#
#     json_sink:
#       enabled: true
#       path: output/json_sink/application.jsonl
#
#     delta_sink:
#       enabled: true
#       table: main.logging.application
#       path: output/delta_sink/application
#
#
# ==============================================================================
# ENVIRONMENT SELECTION
# ==============================================================================
#
# When the MonitAudit configuration loader supports environment selection,
# the application environment can be selected externally.
#
# Supported environment-variable names in the current MonitAudit design:
#
#   MONITAUDIT_ENVIRONMENT
#   MONITAUDIT_ENV
#   ENV
#
# Example:
#
#   MONITAUDIT_ENV=dev uv run python main.py
#
# Do not store secrets, passwords, PyPI tokens, access tokens, connection
# credentials, or other sensitive values directly in this file.
#
# ==============================================================================
# BASIC PYTHON USAGE
# ==============================================================================
#
#   import monitaudit
#
#
#   mta = monitaudit.monitaudit_init()
#
#   mta.info("Application started")
#   mta.debug("Processing data")
#   mta.warning("Example warning")
#
#
# ==============================================================================
````
