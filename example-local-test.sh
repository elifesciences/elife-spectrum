#!/bin/bash
set -e
source venv/bin/activate

export SPECTRUM_PROCESSES=1 # run tests serially
export SPECTRUM_ENVIRONMENT=continuumtest  # required
export SPECTRUM_LOG_LEVEL=DEBUG  # more output
export SPECTRUM_TIMEOUT=60  # speeds up errors

#python -m pytest -s spectrum/test_api.py
python -m pytest -vvv --capture=no spectrum/test_journal_cms.py
