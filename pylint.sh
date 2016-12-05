#!/bin/bash
set -e
source venv/bin/activate && pylint -r n spectrum/ conftest.py

