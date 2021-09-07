#!/bin/bash
set -e
# ARGUMENTS
# --article-id=15600  optional, if you want to filter a particular article

# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
SPECTRUM_PROCESSES=${SPECTRUM_PROCESSES:-4}

# clean up possible previous builds
./reset-build.sh

# sanity check
./pylint.sh

# bulk of the tests
./venv/bin/pytest \
    --verbose \
    --junitxml build/junit.xml \
    --capture=no \
    --numprocesses=$SPECTRUM_PROCESSES \
    spectrum $*
