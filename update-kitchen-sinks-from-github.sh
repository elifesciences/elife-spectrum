#!/bin/bash
# downloads kitchen sink XML and replaces manuscript IDs with template placeholders.
# 'import-xml.sh' writes a file that will be used during elife-spectrum testing.
set -e

commit=${1:-master}

for id in 00777 1234567890
do
    ./download-from-github.sh $id $commit
    ./import-xml.sh $id elife-$id.xml
done
