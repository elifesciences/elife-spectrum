#!/bin/bash
source venv/bin/activate
python -c "from spectrum.aws import clean; clean()"
