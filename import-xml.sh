#!/bin/bash
set -e

if [ "$#" != 2 ]; then
    echo "Usage: ./import-xml.sh ID FILENAME"
    echo "e.g. ./import-xml.sh 1234567890 elife-00666-something.xml"
    exit 1
fi

id="$1"
source_filename="$2"
set -o pipefail
xmllint -format "$source_filename" | sed -e "s/$id/{{ article['id'] }}/g" > "spectrum/templates/elife-$id-vor-r1/elife-$id.xml.jinja"

