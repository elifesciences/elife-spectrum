#!/bin/bash
set -e

# cd to the project's directory so that the script can be run from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

./execute.sh --article-id=15893 -m continuum $*
