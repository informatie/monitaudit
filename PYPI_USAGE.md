## Configuration

MonitAudit uses a `config/monitaudit` directory containing two configuration files:

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

These values define the standard logging and tracing behaviour and normally remain the same across runtime environments.

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

### `monitaudit.runtime`

`monitaudit.runtime` contains application-specific and environment-specific runtime configuration.

Although the file does not use a `.yaml` extension, its contents use YAML syntax.

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

### Selecting an Environment

The runtime environment can be selected using one of the supported environment variables:

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

## Example 1: Minimal Usage

```python
import monitaudit


mta = monitaudit.monitaudit_init()

mta.info("Hello from MonitAudit")
```

## Example 2: Structured Logging

MonitAudit provides standard logging levels through a consistent interface:

```python
import monitaudit


mta = monitaudit.monitaudit_init()

mta.info("Application started")
mta.debug("Processing data")
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

This keeps operational data structured instead of embedding all contextual information into formatted log messages.

## Example 3: Function Tracing

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

Depending on configuration, tracing can capture information such as:

- function start and end events
- execution duration
- function parameters
- return values
- errors and exception details
- tracebacks
- `call_id`
- `parent_call_id`

## Example 4: Error Handling

Application exceptions can be logged explicitly using `mta.error()` while preserving normal exception behaviour:

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

## More Examples

Complete examples, configuration files, sink demonstrations, tracing scenarios, and more advanced usage patterns are available in the dedicated examples repository:

👉 **[monitaudit-examples](https://github.com/informatie/monitaudit-examples)**

The examples repository covers practical scenarios including:

- configuration
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

The examples repository is the recommended starting point for more advanced MonitAudit configuration, tracing, sinks, and application integration.