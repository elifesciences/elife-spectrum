#!/bin/bash
set -e
source venv/bin/activate

export SPECTRUM_PROCESSES=1 # run tests serially
export SPECTRUM_ENVIRONMENT=continuumtest  # or end2end. required.
export SPECTRUM_LOG_LEVEL=DEBUG  # more output
export SPECTRUM_TIMEOUT=60  # seconds. speeds up errors, ~300 is typically best

# run all tests in spectrum/test_journal_cms.py, ignoring anything on stdout
#python -m pytest -vvv --capture=no spectrum/test_journal_cms.py

# run all tests marked with 'journal_cms'
#python -m pytest -vvv -m journal_cms

# run the 'test_adding_article_fragment' test in 'spectrum/test_article.py'
#python -m pytest -vvv spectrum/test_article.py::test_adding_article_fragment 
