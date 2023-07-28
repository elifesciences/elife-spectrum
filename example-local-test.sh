#!/bin/bash
set -e
source venv/bin/activate

export SPECTRUM_PROCESSES=1 # run tests serially
export SPECTRUM_ENVIRONMENT=continuumtest  # or end2end. required.
export SPECTRUM_LOG_LEVEL=DEBUG  # more output
export SPECTRUM_TIMEOUT=300  # seconds. speeds up errors, ~300 is typically best

# generate a simple article and then test it's publication
pytest -vvv spectrum/test_article.py::test_article_first_version[00230]

# run all tests in spectrum/test_journal_cms.py, ignoring anything on stdout
#pytest -vvv --capture=no spectrum/test_journal_cms.py

# run all tests marked with 'journal_cms'
#pytest -vvv -m journal_cms

# run the 'test_adding_article_fragment' test in 'spectrum/test_article.py'
#pytest -vvv spectrum/test_article.py::test_adding_article_fragment

#pytest -vvv spectrum/test_epp.py
