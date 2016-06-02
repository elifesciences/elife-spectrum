#!/bin/bash
source venv/bin/activate
rm -f build/junit.xml
py.test -v --junitxml build/junit.xml -s spectrum
