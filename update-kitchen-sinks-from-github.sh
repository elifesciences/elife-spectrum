#!/bin/bash
set -e

commit=${1:-master}

for id in 00777 00666
do
    ./download-from-github.sh $id $commit
    ./import-xml.sh $id elife-$id.xml
done
