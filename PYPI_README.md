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