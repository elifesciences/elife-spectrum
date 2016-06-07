#!/bin/bash
set -e
# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

source venv/bin/activate
rm -f build/junit.xml
py.test -v --junitxml build/junit.xml -s spectrum
