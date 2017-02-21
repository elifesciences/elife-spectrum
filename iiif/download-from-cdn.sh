#!/bin/bash
set -e

if [ "$#" -ne "2" ]; then
    echo "Usage: $0 list_of_paths.txt folder/"
    exit 1
fi

path=$1
target=$2
echo $path
folder=$target/$(echo $path | grep -o "^[0-9]\+")
mkdir -p $folder
wget -O "$target/${path}" -c "https://publishing-cdn.elifesciences.org/$path"
