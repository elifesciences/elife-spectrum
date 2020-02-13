#!/bin/bash
set -e

source venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.lock.new
# https://stackoverflow.com/questions/39577984/what-is-pkg-resources-0-0-0-in-output-of-pip-freeze-command
sed -i "/^pkg-resources==.*/d" requirements.lock.new
sed -i -e "s|^econtools==.*|$(cat requirements.txt | grep egg=econtools)|" requirements.lock.new
sed -i -e "s|^spectrumprivate==.*|$(cat requirements.txt | grep egg=spectrumprivate)|" requirements.lock.new
mv requirements.lock.new requirements.lock
