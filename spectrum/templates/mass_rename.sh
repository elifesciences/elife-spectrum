#!/bin/bash
# lsh@2021-09: script was used once in 2016 to rename files in templates.
# candidate for deletion.
for article in elife-*-???-v?; do
    for file in $article/elife*-v?.*; do
        mv "$file" "${file/-v?./.}";
    done
done
