#!/bin/bash
set -e
source prerequisites.sh

if [ ! git lfs ]; then
    echo "could not find git-lfs"
fi

if [ ! -e "venv/bin/python2.7" ]; then
    echo "could not find venv/bin/python2.7, recreating venv"
    rm -rf venv
    virtualenv --python=python2.7 venv
fi

source venv/bin/activate
if pip list | grep econtools; then
    pip uninstall -y econtools
fi
pip install -r requirements.txt

docker-compose up -d --force-recreate
