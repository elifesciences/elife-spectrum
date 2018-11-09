#!/bin/bash
set -e

# clean up possible build results to avoid confusion 
# on further builds picking them up
rm -f build/junit.xml
rm -f build/test.log
rm -f build/screenshots/*.png
