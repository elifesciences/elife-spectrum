#!/bin/bash
set -e
# ARGUMENTS
# --article-id=15600  optional, if you want to filter a particular article

# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

rm -f build/junit.xml
rm -f build/test.log
rm -rf /tmp/elife-*
venv/bin/py.test -v --junitxml build/junit.xml -s -n 2 spectrum $*
