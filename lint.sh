#!/bin/bash
set -e
source venv/bin/activate
pylint --reports=n spectrum/ conftest.py
