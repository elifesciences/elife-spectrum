#!/bin/bash
# ARGUMENTS
# --article-id=15600  optional, if you want to filter a particular article

set -e
# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

rm -f build/junit.xml
venv/bin/py.test -v --junitxml build/junit.xml -n 2 -s spectrum $*
