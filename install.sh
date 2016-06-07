#!/bin/bash
set -e
source prerequisites.sh

virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
