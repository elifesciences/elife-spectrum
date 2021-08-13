#!/bin/bash
set -e

commit=${1:-master}

for id in 00777 1234567890
do
    ./download-from-github.sh $id $commit
    ./import-xml.sh $id elife-$id.xml
done
