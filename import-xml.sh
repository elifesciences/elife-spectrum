#!/bin/bash
# used to format the kitchen sink XML and replace mentions of the manuscript ID with a Jinja template placeholder.
# see 'update-kitchen-sinks-from-github.sh'
set -e

if [ "$#" != 2 ]; then
    echo "Usage: ./import-xml.sh ID FILENAME"
    echo "e.g. ./import-xml.sh 00666 elife-00666-something.xml"
    exit 1
fi

id="$1"
source_filename="$2"
set -o pipefail
xmllint -format "$source_filename" | sed -e "s/$id/{{ article['id'] }}/g" > "spectrum/templates/elife-$id-vor-r1/elife-$id.xml.jinja"
