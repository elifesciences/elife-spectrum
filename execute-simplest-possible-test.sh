#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

#./pylint.sh
SPECTRUM_LOG_LEVEL=DEBUG venv/bin/py.test -v -s spectrum/test_article.py::test_article_first_version --article-id=15893 --assert=plain $*
