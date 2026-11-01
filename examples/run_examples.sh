#!/usr/bin/env bash

set -euo pipefail

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

EXAMPLES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${EXAMPLES_DIR}/.." && pwd)"

CONFIG_DIR="${EXAMPLES_DIR}/config"
DATA_DIR="${EXAMPLES_DIR}/data"
SCRIPTS_DIR="${EXAMPLES_DIR}/scripts"
OUTPUT_DIR="${EXAMPLES_DIR}/output"

ENVIRONMENT="dev"


# ---------------------------------------------------------------------------
# Select environment
# ---------------------------------------------------------------------------

select_environment() {
    echo
    echo "Select MonitAudit environment:"
    echo
    echo "  1) dev"
    echo "  2) acc"
    echo "  3) prod"
    echo

    read -r -p "Environment [1]: " choice

    case "${choice:-1}" in
        1)
            ENVIRONMENT="dev"
            ;;
        2)
            ENVIRONMENT="acc"
            ;;
        3)
            ENVIRONMENT="prod"
            ;;
        *)
            echo "Invalid environment."
            return 1
            ;;
    esac
}


# --------------------------------------------------------------------------ind examples
# ---------------------------------------------------------------------------

find_examples() {
    find "${SCRIPTS_DIR}" \
        -type f \
        -name 'main_*.py' \
        ! -name 'main_load_config.py' \
        | sort
}


# ---------------------------------------------------------------------------
# Run example
# ---------------------------------------------------------------------------

run_example() {
    local file="$1"
    local relative

    relative="${file#"${EXAMPLES_DIR}/"}"

    clear

    echo "======================================================================"
    echo "MonitAudit Example"
    echo "======================================================================"
    echo
    echo "Environment : ${ENVIRONMENT}"
    echo "Working dir : ${EXAMPLES_DIR}"
    echo "Example     : ${relative}"
    echo
    echo "======================================================================"
    echo

    cd "${EXAMPLES_DIR}"

    PYTHONPATH="${SCRIPTS_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    MONITAUDIT_ENV="${ENVIRONMENT}" \
        uv run python "${relative}"

    echo
    read -r -p "Press Enter to continue..."
}


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

show_menu() {
    while true; do
        mapfile -t examples < <(find_examples)

        clear

        echo "======================================================================"
        echo "                       MonitAudit Examples"
        echo "======================================================================"
        if [ "${choice}" -eq 0 ]; then
            echo
        else
            echo "Menu option : ${choice}"
        fi
        echo "Environment : ${ENVIRONMENT}"
        echo "Working dir : ${EXAMPLES_DIR}"
        echo

        if [ "${#examples[@]}" -eq 0 ]; then
            echo "No main_*.py examples found."
            exit 1
        fi

        # -------------------------------------------------------------------
        # Determine maximum example-name width
        # -------------------------------------------------------------------

        max_name_length=0

        for file in "${examples[@]}"; do
            name="$(basename "${file}" .py)"

            if [ "${#name}" -gt "${max_name_length}" ]; then
                max_name_length="${#name}"
            fi
        done

        # Add some spacing between the two columns.
        column_gap=6

        # -------------------------------------------------------------------
        # Determine groups
        # -------------------------------------------------------------------

        groups=()

        for file in "${examples[@]}"; do
            relative="${file#"${SCRIPTS_DIR}/"}"
            group="$(dirname "${relative}")"

            found=false

            for existing_group in "${groups[@]}"; do
                if [ "${existing_group}" = "${group}" ]; then
                    found=true
                    break
                fi
            done

            if [ "${found}" = false ]; then
                groups+=("${group}")
            fi
        done

        # -------------------------------------------------------------------
        # Display examples grouped in two columns
        # -------------------------------------------------------------------

        for group in "${groups[@]}"; do
            group_indices=()

            for i in "${!examples[@]}"; do
                file="${examples[$i]}"
                relative="${file#"${SCRIPTS_DIR}/"}"
                file_group="$(dirname "${relative}")"

                if [ "${file_group}" = "${group}" ]; then
                    group_indices+=("${i}")
                fi
            done

            echo
            echo "  [${group^^}]"
            echo

            count="${#group_indices[@]}"
            rows=$(((count + 1) / 2))

            for ((row = 0; row < rows; row++)); do
                # -----------------------------------------------------------
                # Left column
                # -----------------------------------------------------------

                left_index="${group_indices[$row]}"
                left_file="${examples[$left_index]}"
                left_name="$(basename "${left_file}" .py)"
                left_number=$((left_index + 1))

                printf "  %2d) %-*s" \
                    "${left_number}" \
                    "${max_name_length}" \
                    "${left_name}"

                # -----------------------------------------------------------
                # Right column
                # -----------------------------------------------------------

                right_position=$((row + rows))

                if [ "${right_position}" -lt "${count}" ]; then
                    right_index="${group_indices[$right_position]}"
                    right_file="${examples[$right_index]}"
                    right_name="$(basename "${right_file}" .py)"
                    right_number=$((right_index + 1))

                    printf "%*s%2d) %s" \
                        "${column_gap}" \
                        "" \
                        "${right_number}" \
                        "${right_name}"
                fi

                echo
            done
        done

        echo
        echo "----------------------------------------------------------------------"
        echo "   e) Change environment"
        echo "   q) Quit"
        echo

        read -r -p "Select example: " choice

        case "${choice}" in
            q|Q)
                echo
                exit 0
                ;;

            e|E)
                select_environment
                ;;

            *)
                if [[ "${choice}" =~ ^[0-9]+$ ]]; then
                    index=$((choice - 1))

                    if [ "${index}" -ge 0 ] &&
                       [ "${index}" -lt "${#examples[@]}" ]; then
                        run_example "${examples[$index]}"
                    else
                        echo "Invalid selection."
                        sleep 1
                    fi
                else
                    echo "Invalid selection."
                    sleep 1
                fi
                ;;
        esac
    done
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    if [ ! -d "${EXAMPLES_DIR}" ]; then
        echo "ERROR: examples directory not found:"
        echo "       ${EXAMPLES_DIR}"
        exit 1
    fi

    if [ ! -d "${SCRIPTS_DIR}" ]; then
        echo "ERROR: scripts directory not found:"
        echo "       ${SCRIPTS_DIR}"
        exit 1
    fi

    mkdir -p "${OUTPUT_DIR}"

    cd "${EXAMPLES_DIR}"

    select_environment
    show_menu
}


main