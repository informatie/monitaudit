#!/usr/bin/env bash

set -euo pipefail

EXAMPLES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${EXAMPLES_DIR}/.." && pwd)"

ENVIRONMENT="dev"


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


find_examples() {
    find "${EXAMPLES_DIR}" \
        -type f \
        -name 'main_*.py' \
        | sort
}


run_example() {
    local file="$1"
    local relative

    relative="${file#"${PROJECT_ROOT}/"}"

    clear

    echo "======================================================================"
    echo "MonitAudit Example"
    echo "======================================================================"
    echo
    echo "Environment : ${ENVIRONMENT}"
    echo "Example     : ${relative}"
    echo
    echo "======================================================================"
    echo

    cd "${PROJECT_ROOT}"

    MONITAUDIT_ENV="${ENVIRONMENT}" \
        uv run python "${relative}"

    echo
    read -r -p "Press Enter to continue..."
}


show_menu() {
    while true; do
        mapfile -t examples < <(find_examples)

        clear

        echo "======================================================================"
        echo "                       MonitAudit Examples"
        echo "======================================================================"
        echo
        echo "Environment : ${ENVIRONMENT}"
        echo

        if [ "${#examples[@]}" -eq 0 ]; then
            echo "No main_*.py examples found."
            exit 1
        fi

        current_group=""

        for i in "${!examples[@]}"; do
            file="${examples[$i]}"
            relative="${file#"${EXAMPLES_DIR}/"}"
            group="$(dirname "${relative}")"
            name="$(basename "${relative}" .py)"

            if [ "${group}" != "${current_group}" ]; then
                current_group="${group}"

                echo
                echo "  [${group^^}]"
                echo
            fi

            printf "  %2d) %s\n" \
                "$((i + 1))" \
                "${name}"
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


main() {
    if [ ! -d "${EXAMPLES_DIR}" ]; then
        echo "ERROR: examples directory not found:"
        echo "       ${EXAMPLES_DIR}"
        exit 1
    fi

    select_environment
    show_menu
}


main