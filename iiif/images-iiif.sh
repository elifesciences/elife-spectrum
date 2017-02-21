#!/bin/bash
set -e

if [ "$#" -ne "2" ]; then
    echo "Usage: $0 list_of_paths.txt target/"
    exit 1
fi

cat $1 | xargs -P 8 -I {} ./image-iiif.sh {} $2
