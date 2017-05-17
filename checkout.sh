#!/bin/bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: ./checkout.sh SHA1"
    exit 1
fi

revision=${1:-master}

git fetch
git checkout ${revision}
git reset --hard
git lfs pull
./install.sh
