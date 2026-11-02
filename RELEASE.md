# MonitAudit Release History

This document provides the release history of MonitAudit.

MonitAudit follows Semantic Versioning:

- **MAJOR** – incompatible or fundamental architectural changes
- **MINOR** – new functionality added in a backwards-compatible manner
- **PATCH** – backwards-compatible fixes, improvements and maintenance

---
## 1.3.0 - ????-??-??

### Changed

- usage.md text updated and file renamed.
- readme.md text updated and file renamed.
- link github monitaudit-examples added.
- release.sh fixed.
- examples of the config and runtime settings in README.md.
- used AI to verify the code (sometime more comment)
- used AI to verify bugs (some bugs fixed)
- ConsoleSink error im parameters, could lead to error
- pytest, now 100%
- monitaudit_init added, simple call

## 1.2.4 - 2026-11-01

### Changed

- Standardised example project structure.
- Standardised example configuration loading.
- Centralised example directory handling.
- Updated runtime configuration structure.
- Improved environment selection using `MONITAUDIT_ENV`.
- Standardised sink output directories.
- Updated JsonSink, FileSink and DeltaSink examples.
- Improved example verification and diagnostics.
- Continued Ruff, mypy and Pyright strict-mode cleanup.

---

## 1.2.3 - 2026-09-27

### Changed

- Improved runtime configuration validation.
- Improved sink configuration handling.
- Improved structured logging examples.
- Extended configuration error diagnostics.
- General code quality and typing improvements.

---

## 1.2.2 - 2026-08-23

### Added

- Additional tracing examples.
- Additional sink usage examples.
- Extended JSON-safe value handling.

### Changed

- Improved trace context handling.
- Improved parameter serialisation.

---

## 1.2.1 - 2026-07-19

### Fixed

- Improved sink failure isolation.
- Improved exception handling.
- Improved traceback preservation.
- Various logging and tracing stability fixes.

---

## 1.2.0 - 2026-06-14

### Added

- Extended sink architecture.
- Structured configuration of multiple sinks.
- FileSink support.
- JsonSink support.
- DeltaSink integration.
- Configurable sink failure behaviour.

### Changed

- Refined MonitAudit construction and configuration.

---

## 1.1.4 - 2026-05-10

### Changed

- Improved redaction of sensitive parameters.
- Improved maximum parameter length handling.
- Improved JSON-safe conversion.
- Extended validation around structured parameters.

---

## 1.1.3 - 2026-04-05

### Added

- Threading examples.
- Concurrent tracing examples.

### Changed

- Improved trace isolation between threads.
- Improved context propagation.

---

## 1.1.2 - 2026-03-01

### Changed

- Improved nested trace handling.
- Improved function start/end/error logging.
- Improved exception processing.
- Extended automated tests.

---

## 1.1.1 - 2026-01-25

### Fixed

- Logging stability improvements.
- Trace context fixes.
- Sink error handling improvements.
- Configuration validation improvements.

---

## 1.1.0 - 2025-12-21

### Added

- Structured tracing with `@mta.trace`.
- Nested operation tracing.
- Function timing.
- Function parameter logging.
- Structured function result logging.
- Structured exception logging.

### Changed

- Expanded structured log context.

---

## 1.0.0 - 2025-11-16

### Added

- Stable public MonitAudit logging interface.
- Structured INFO, WARNING and ERROR logging.
- Application-level configuration.
- Configurable logging levels.
- Initial production-oriented architecture.

### Changed

- Consolidated logging and observability components.
- Stabilised core configuration model.

---

## 0.5.0 - 2025-10-12

### Added

- Multi-sink logging architecture.
- Sink abstraction.
- Console sink configuration.
- Structured log routing.

### Changed

- Separated logging API from output implementations.

---

## 0.4.0 - 2025-09-07

### Added

- Runtime configuration support.
- Environment-specific configuration.
- YAML-based application configuration.

### Changed

- Configuration responsibilities separated from logging implementation.

---

## 0.3.0 - 2025-08-03

### Added

- Structured log context.
- Application metadata.
- Additional structured logging fields.

### Changed

- Improved log record modelling.
- Improved validation of structured log data.

---

## 0.2.0 - 2025-06-29

### Added

- Initial structured logging models.
- Console logging support.
- Log-level support.
- Basic exception logging.

### Changed

- Refined core logging API.

---

## 0.1.0 - 2025-05-25

### Added

- Initial MonitAudit project structure.
- Initial logging API.
- Basic structured log records.
- Initial configuration support.
- Initial automated test infrastructure.

---

# Versioning

MonitAudit uses the following version format:

`MAJOR.MINOR.PATCH`

For example:

`1.2.4`

where:

- `1` represents the major version.
- `2` represents the minor version.
- `4` represents the patch version.

Release versions are intended to provide a clear indication of compatibility and the scope of changes between releases.