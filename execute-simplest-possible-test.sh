#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

SPECTRUM_LOG_LEVEL=DEBUG ./venv/bin/pytest \
    --verbose \
    --capture=no \
    spectrum/test_article.py::test_article_first_version --article-id=15893 $*
