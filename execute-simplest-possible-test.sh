#!/bin/bash
set -e

# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

venv/bin/py.test -v -s spectrum/test_article.py::test_article_first_version --article-id=15893
