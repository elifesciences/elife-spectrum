#!/bin/bash
set -e
source venv/bin/activate

export SPECTRUM_PROCESSES=1 # run tests serially
export SPECTRUM_ENVIRONMENT=continuumtest  # mandatory
export SPECTRUM_LOG_LEVEL=DEBUG  # more output
export SPECTRUM_TIMEOUT=60  # speeds up errors

#python -m pytest -s spectrum/test_api.py
python -m pytest -vvv -s spectrum/test_article.py::test_bioprotocol_has_protocol_data
