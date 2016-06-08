#!/bin/bash
set -e
# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

venv/bin/python -c 'from spectrum import cleaner; cleaner.everything()'
