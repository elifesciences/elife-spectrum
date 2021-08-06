#!/bin/bash
# used to download specific revisions of the kitchen sink XML from the 'xml-mapping' repository.
# see 'update-kitchen-sinks-from-github.sh'
set -e

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <ARTICLE_ID> [COMMIT]"
    echo "e.g.: $0 00666"
    echo "e.g.: $0 00666 hea6c3fe88bfec137a4bbeda98018c4c074ab893f"
    exit 1
fi

id="$1"
commit="${2-master}"
filename="elife-$id.xml"
url="https://raw.githubusercontent.com/elifesciences/XML-mapping/$commit/$filename"
wget "$url" --output-document "$filename"
echo "$filename"
