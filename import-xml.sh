#!/bin/bash
# used to format the kitchen sink XML and replace mentions of the manuscript ID with a Jinja template placeholder.
# see 'update-kitchen-sinks-from-github.sh'
set -eo pipefail

if [ "$#" != 2 ]; then
    echo "Usage: ./import-xml.sh ID FILENAME"
    echo "e.g. ./import-xml.sh 1234567890 elife-00666-something.xml"
    exit 1
fi

id="$1"
source_filename="$2"

# what is this crazy thing doing?
# 1. formatting the XML using xmllint
# 2. finding all matches for the given '$id' value
# 3. *excluding* matches that contain '<media mimetype=\"video\"' 
# 4. replacing the '$id' value with a jinja expression '{{ article['id'] }}'
# 5. writing the result to the matching test template

xmllint -format "$source_filename" | sed -e "/<media mimetype=\"video\"/!s/$id/{{ article['id'] }}/g" > "spectrum/templates/elife-$id-vor-r1/elife-$id.xml.jinja"
