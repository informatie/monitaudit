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