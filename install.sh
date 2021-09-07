#!/bin/bash
set -e
source prerequisites.sh

if [ ! -e "venv/bin/python3" ]; then
    echo "could not find venv/bin/python3, recreating venv"
    rm -rf venv
    virtualenv --python=python3.6 venv
fi

source venv/bin/activate
if pip list | grep econtools; then
    pip uninstall -y econtools
fi
pip install -r requirements.lock

docker-compose up -d --force-recreate
