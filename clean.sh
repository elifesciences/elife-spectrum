#!/bin/bash
set -e
# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

source venv/bin/activate
python -c "from spectrum.aws import clean; clean()"
