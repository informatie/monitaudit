"""
monitaudit sensitive-parameters redaction example.

Purpose
-------
Demonstrates sensitive parameter redaction while processing the workspace
and element example dataset.

The dataset is loaded from:

    examples/data/example_dataset.yaml

The monitaudit configuration is loaded from:

    examples/config/main_sensitive_parameters_redaction.yaml

Each workspace and its elements are processed normally. During element
processing, example credentials are passed to a traced function to
demonstrate that sensitive values are redacted before trace parameters are
written to the configured monitaudit sinks.

The traced function itself still receives the original values.

Demonstrates
------------
- example-specific monitaudit configuration
- loading the example dataset from YAML
- workspace and element processing
- automatic redaction in @obs.trace
- password redaction
- token redaction
- client_secret redaction
- nested dictionary redaction
- preservation of non-sensitive parameters
- original values remaining available inside the function

Use this example when
---------------------
- validating redaction after changing redaction.py
- checking FileSink output
- checking JsonSink output
- checking DeltaSink parameters
- demonstrating that credentials are not written as trace parameters

Do not use this example when
----------------------------
- checking arbitrary secrets embedded in exception messages
- checking secrets manually placed into log messages
- assuming monitaudit sanitises every arbitrary string

Automatic redaction protects traced parameters according to the monitaudit
redaction rules. Sensitive information should never deliberately be placed
in log messages or exception messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from monitaudit.utilities.build_monitaudit import (
    build_monitaudit,
)


EXAMPLE_DIR = Path(__file__).parent

DATASET_PATH = (
    EXAMPLE_DIR
    / "data"
    / "example_dataset.yaml"
)

CONFIG_PATH = (
    EXAMPLE_DIR
    / "config"
    / "main_sensitive_parameters_redaction.yaml"
)


def load_dataset() -> dict[str, Any]:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(
            f"Example dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid dataset format: {DATASET_PATH}"
        )

    workspaces = data.get("workspaces")

    if not isinstance(workspaces, list):
        raise ValueError(
            "Dataset does not contain a valid "
            f"'workspaces' list: {DATASET_PATH}"
        )

    return data


def main() -> None:
    obs = build_monitaudit(
        CONFIG_PATH
    )

    @obs.trace
    def process_element(
        ws_nummer: int,
        element_code: str,
        element_name: str,
        database_password: str,
        access_token: str,
        config: dict[str, Any],
    ) -> None:
        """
        Process one element using example credentials.

        The original credential values remain available to the function.
        monitaudit only redacts the captured representation written to sinks.
        """

        assert (
            database_password
            == "example-password"
        )

        assert (
            access_token
            == "example-access-token"
        )

        assert (
            config["client_secret"]
            == "example-client-secret"
        )

        credentials = config["credentials"]

        if not isinstance(
            credentials,
            dict,
        ):
            raise ValueError(
                "Example credentials must be a mapping."
            )

        assert (
            credentials["password"]
            == "nested-password"
        )

        # Non-sensitive values remain available as normal.
        assert config["timeout"] == 30

        # Simulate element processing.
        _ = ws_nummer
        _ = element_code
        _ = element_name

    obs.info(
        "Redaction example started",
        example="main_sensitive_parameters_redaction",
    )

    dataset = load_dataset()
    workspaces = dataset["workspaces"]

    obs.info(
        "Dataset loaded",
        dataset_path=str(DATASET_PATH),
        workspace_count=len(workspaces),
    )

    for workspace in workspaces:
        if not isinstance(
            workspace,
            dict,
        ):
            raise ValueError(
                "Each workspace must be a mapping."
            )

        ws_nummer = workspace["ws_nummer"]
        ws_naam = workspace["ws_naam"]
        elements = workspace["elements"]

        if not isinstance(
            elements,
            list,
        ):
            raise ValueError(
                f"Workspace {ws_nummer!r} "
                "'elements' must be a list."
            )

        obs.info(
            "Processing workspace",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            element_count=len(elements),
        )

        for element in elements:
            if not isinstance(
                element,
                dict,
            ):
                raise ValueError(
                    f"Workspace {ws_nummer!r} "
                    "contains an invalid element."
                )

            process_element(
                ws_nummer=ws_nummer,
                element_code=element["element_code"],
                element_name=element["element_name"],
                database_password="example-password",
                access_token="example-access-token",
                config={
                    "client_secret": (
                        "example-client-secret"
                    ),
                    "timeout": 30,
                    "credentials": {
                        "username": "example-user",
                        "password": "nested-password",
                    },
                },
            )

        obs.info(
            "Workspace completed",
            ws_nummer=ws_nummer,
            ws_naam=ws_naam,
            processed_elements=len(elements),
        )

    obs.info(
        "Redaction example completed",
        workspace_count=len(workspaces),
    )


def print_summary() -> None:
    print(
        "\n"
        "=== Example completed: parameters redaction ===\n"
        "\n"
        "What was demonstrated:\n"
        "  - example-specific monitaudit configuration\n"
        "  - example dataset loaded from YAML\n"
        "  - workspaces and elements processed\n"
        "  - element processing traced\n"
        "  - sensitive traced parameters are redacted\n"
        "  - passwords are stored as ***\n"
        "  - tokens are stored as ***\n"
        "  - client secrets are stored as ***\n"
        "  - nested sensitive values are redacted\n"
        "  - non-sensitive parameters remain visible\n"
        "  - traced function receives the original values\n"
        "\n"
        "Where to look for the results:\n"
        "  - Console: inspect trace output\n"
        "  - JSON: var/log/examples/"
        "main_sensitive_parameters_redaction.jsonl\n"
        "  - File: var/log/examples/"
        "main_sensitive_parameters_redaction.log\n"
        "\n"
        "Expected visible trace parameters:\n"
        "  ws_nummer     = normal value\n"
        "  element_code  = normal value\n"
        "  element_name  = normal value\n"
        "  timeout       = 30\n"
        "  username      = example-user\n"
        "\n"
        "Expected redacted trace parameters:\n"
        '  database_password = "***"\n'
        '  access_token      = "***"\n'
        '  client_secret     = "***"\n'
        '  password          = "***"\n'
        "\n"
        "IMPORTANT:\n"
        "  example-password\n"
        "  example-access-token\n"
        "  example-client-secret\n"
        "  nested-password\n"
        "\n"
        "  must not occur in captured trace parameters.\n"
        "\n"
        "Dataset:\n"
        "  examples/data/example_dataset.yaml\n"
        "\n"
        "Configuration:\n"
        "  examples/config/"
        "main_sensitive_parameters_redaction.yaml\n"
    )


if __name__ == "__main__":
    main()
    print_summary()