#!/bin/bash
set -e
source prerequisites.sh
source mkvenv.sh
source venv/bin/activate

pip install pip wheel --upgrade
pip install -r requirements.txt

docker-compose up -d --force-recreate
