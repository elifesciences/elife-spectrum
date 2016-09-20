#!/bin/bash
set -e

users=${1:-10}
time=${2:-60}

siege -c${users} -t${time}S http://end2end--journal.elifesciences.org/content/4/e10627
