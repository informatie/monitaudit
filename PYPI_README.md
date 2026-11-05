# monitaudit 🔍 🛡️

A lightweight Python observability and audit framework providing standardized tracing, correlation, safe structured events, and configurable sinks.

`monitaudit` provides a clear, developer-friendly API for structured logging, application tracing, runtime diagnostics, and audit events.

It is designed to keep observability concerns explicit and consistent without spreading logging and tracing logic throughout application code.

## Key Highlights

- **Structured Logging**  
  Capture consistent structured application events with contextual data that can be processed, queried, and analysed.

- **Function Tracing**  
  Trace function execution using start, end, and error events, including execution duration and optional parameter and return-value capture.

- **Correlation and Nested Tracing**  
  Correlate related operations using `call_id` and `parent_call_id` relationships across nested function calls.

- **Exception Diagnostics**  
  Capture structured exception information and tracebacks while preserving normal application exception behaviour.

- **Sensitive Data Protection**  
  Protect passwords, tokens, secrets, and other sensitive values when capturing function parameters and structured data.

- **Audit Tracking**  
  Record important application actions, events, and state changes for operational and audit purposes.

- **Configurable Sinks**  
  Route structured events to configurable output destinations.

- **Sink Failure Isolation**  
  Configure how sink failures are handled so observability failures do not unnecessarily disrupt application logic.

- **Modern Python**  
  Designed around type annotations, explicit APIs, structured models, and modern Python development practices.

## Installation

Install `monitaudit` from PyPI using `uv`:

```bash
uv add monitaudit
```

Or using `pip`:

```bash
pip install monitaudit
```

## Configuration

MonitAudit uses a `config/monitaudit` directory containing its default and runtime configuration:

```text
your-application/
├── config/
│   └── monitaudit/
│       ├── monitaudit.properties
│       └── monitaudit.runtime
└── main.py
```

The two configuration files have separate responsibilities:

- `monitaudit.properties` defines the standard MonitAudit defaults.
- `monitaudit.runtime` defines application-specific and environment-specific runtime configuration.

### `monitaudit.properties`

`monitaudit.properties` contains the default MonitAudit configuration.

These values define standard logging and tracing behaviour and normally remain the same across runtime environments.

Example:

```properties
# config/monitaudit/monitaudit.properties

logging.level=INFO
logging.timer=true
logging.show_parameters=true
logging.max_parameter_length=1000
logging.sink_failure_mode=continue
logging.file_cycle=10
```

These settings control behaviour such as:

- logging level
- execution timing
- function parameter capture
- maximum captured parameter length
- sink failure handling
- file lifecycle behaviour

For example:

```properties
logging.show_parameters=true
```

controls whether function parameters may be included in trace events.

The maximum captured parameter length can be limited using:

```properties
logging.max_parameter_length=1000
```

### `monitaudit.runtime`

`monitaudit.runtime` contains application-specific and environment-specific runtime configuration.

Although the runtime file does not use a `.yaml` extension, its contents use YAML syntax.

Example:

```yaml
# config/monitaudit/monitaudit.runtime

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

This allows the same application to use different MonitAudit settings without changing application code.

### Selecting an Environment

The runtime environment can be selected using one of the supported environment variables.

Using `MONITAUDIT_ENVIRONMENT`:

```bash
export MONITAUDIT_ENVIRONMENT=dev
```

Alternatively:

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

The selected environment determines which environment-specific runtime configuration is applied.

## Basic Usage

A minimal MonitAudit application requires only initialization and a log event:

```python
import monitaudit


mta = monitaudit.monitaudit_init()

mta.info("Hello from MonitAudit")
```

The resulting MonitAudit instance can be shared by the application for structured logging and tracing.

## Structured Logging

MonitAudit provides standard logging levels through a consistent interface:

```python
import monitaudit


mta = monitaudit.monitaudit_init()

mta.debug("Processing data")
mta.info("Application started")
mta.warning("Example warning")
mta.error("Example error")
```

Structured application data can be attached to events:

```python
mta.info(
    "Order processed",
    order_id="ORD-1001",
    customer_id="CUST-42",
    status="completed",
)
```

Keeping operational data structured makes events easier to process, filter, query, and analyse than embedding all information into formatted message strings.

## Function Tracing

Use `@mta.trace` to instrument application functions:

```python
import monitaudit


mta = monitaudit.monitaudit_init()


@mta.trace
def calculate_total(price: float, quantity: int) -> float:
    return price * quantity


def main() -> None:
    mta.info("Application started")

    total = calculate_total(12.50, 4)

    mta.info(
        "Calculation completed",
        total=total,
    )

    mta.info("Application completed")


if __name__ == "__main__":
    main()
```

Tracing allows application execution to be recorded consistently without manually implementing start, end, duration, and error logging inside every function.

Depending on configuration, trace events can include information such as:

- function start
- function end
- function error
- execution duration
- function parameters
- return values
- exception details
- tracebacks
- `call_id`
- `parent_call_id`

## Nested Tracing

Traced functions can call other traced functions.

MonitAudit can correlate these operations through `call_id` and `parent_call_id` relationships.

For example:

```python
import monitaudit


mta = monitaudit.monitaudit_init()


@mta.trace
def calculate_tax(amount: float) -> float:
    return amount * 0.21


@mta.trace
def calculate_total(amount: float) -> float:
    tax = calculate_tax(amount)
    return amount + tax


def main() -> None:
    total = calculate_total(100.0)

    mta.info(
        "Calculation completed",
        total=total,
    )


if __name__ == "__main__":
    main()
```

This creates a relationship between the parent `calculate_total()` call and the nested `calculate_tax()` call.

## Error Handling

Application exceptions can be logged explicitly through `mta.error()` while preserving the application's normal exception behaviour.

```python
import monitaudit


mta = monitaudit.monitaudit_init()


def process_data() -> None:
    raise RuntimeError("Processing failed")


def main() -> None:
    mta.info("Application started")

    try:
        process_data()
    except Exception as exc:
        mta.error(
            "Application failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise


if __name__ == "__main__":
    main()
```

For traced functions, MonitAudit can capture structured error and traceback information as part of the trace lifecycle.

For example:

```python
import monitaudit


mta = monitaudit.monitaudit_init()


@mta.trace
def process_data() -> None:
    raise RuntimeError("Processing failed")


def main() -> None:
    process_data()


if __name__ == "__main__":
    main()
```

The tracing layer can record the failed function call while allowing the original exception to propagate normally.

## Parameter Capture

Function parameter capture can be enabled through:

```properties
logging.show_parameters=true
```

For example:

```python
@mta.trace
def calculate_total(price: float, quantity: int) -> float:
    return price * quantity
```

When parameter capture is enabled, the trace can include contextual information about the function invocation.

Parameter values can be bounded using:

```properties
logging.max_parameter_length=1000
```

This prevents unexpectedly large parameter representations from producing excessively large observability events.

## Sensitive Data

Observability data should never expose credentials or other sensitive information.

Parameters such as:

```text
password
token
secret
```

should be protected when trace parameters or structured application data are captured.

Avoid explicitly logging secrets:

```python
# Avoid
mta.info(
    "Login attempt",
    password=password,
    token=token,
)
```

Prefer non-sensitive identifiers and operational context:

```python
mta.info(
    "Login completed",
    user_id=user_id,
    status="success",
)
```

This provides useful observability information without intentionally placing credentials in structured events.

## Configurable Sinks

MonitAudit can route events to configured sinks.

This separates event creation from event delivery:

```text
Application
    │
    ▼
 MonitAudit
    │
    ├── Console
    ├── File
    ├── JSON
    ├── Delta
    └── Memory
```

Application code can therefore use the same logging and tracing interface regardless of the configured output destination.

Sink configuration belongs in the MonitAudit configuration rather than being spread throughout application code.

## Sink Failure Handling

Sink failure behaviour can be controlled through:

```properties
logging.sink_failure_mode=continue
```

Using `continue` allows application execution to continue when an observability sink fails.

This helps maintain an important separation:

> Failure of the observability layer should not unnecessarily become failure of the observed application.

The appropriate failure policy should still be selected based on the application's operational and audit requirements.

## Local Development

When developing MonitAudit and a consuming application on the same machine, install the local project as an editable dependency:

```bash
uv add --editable /home/zadmin/projects/monitaudit
```

The consuming application then uses the local MonitAudit source directly.

This allows library changes to be tested immediately without publishing a new package release to PyPI.

## Examples

Complete examples, configuration files, sink demonstrations, tracing scenarios, and integration patterns are maintained in the dedicated examples repository:

👉 **[monitaudit-examples](https://github.com/informatie/monitaudit-examples)**

The examples repository provides practical demonstrations of:

- MonitAudit configuration
- structured logging
- function tracing
- parameter capture
- sensitive-value redaction
- nested tracing
- `call_id` and `parent_call_id`
- execution duration
- return values
- exception handling
- traceback capture
- handled child failures
- parent trace continuation
- configurable sinks

The examples repository is the recommended starting point for learning how to configure and integrate MonitAudit into an application.

## Project Philosophy

MonitAudit is not intended to replace application logic or become a general-purpose application framework.

Its responsibility is deliberately focused:

> Provide applications with a lightweight, consistent observability and audit layer for structured events, tracing, correlation, diagnostics, and configurable event delivery.

Application code should focus on business behaviour.

MonitAudit should provide the surrounding observability needed to understand that behaviour.

## License

See the `LICENSE` file for the project's licensing terms.