#!/bin/bash
set -e

if [ "$#" -ne "1" ]; then
    echo "Usage: $0 list_of_paths.txt"
    exit 1
fi

path=$1
echo $path
folder=images/$(echo $path | grep -o "^[0-9]\+")
mkdir -p $folder
wget -O "images/${path}.jpg" -c "https://ci--lax.elifesciences.org/iiif/$path/full/560,/0/default.jpg"
