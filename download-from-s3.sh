#!/bin/bash
set -e

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <ARTICLE_ID> [<BUCKET>]"
    echo "e.g.: $0 00666"
    echo "e.g.: $0 00666 ct-elife-production-final"
    exit 1
fi

id="$1"
bucket="${2:-ct-elife-production-final}"
latest_revision=$(aws s3 ls "s3://${bucket}/elife-${id}-" | awk '{print $4}' | sed -e 's/^.*-r\([0-9]*\)\.zip/\1/g' | sort -n | tail -n 1)
filename="elife-${id}-vor-r${latest_revision}.zip"
canonical_filename="elife-${id}-vor-r1.zip"
aws s3 cp "s3://${bucket}/${filename}" .
mv "${filename}" "${canonical_filename}"
