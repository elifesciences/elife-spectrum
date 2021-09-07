#!/bin/bash
set -e
which xmllint || (
    echo "xmllint not found. Try installing the libxml2-utils package"
    exit 1
)
