#!/bin/bash
set -e

for id in 00777 00666
do
    ./download-from-s3.sh $id
    ./import.sh elife-$id-vor-r1.zip
done

git add spectrum/templates
