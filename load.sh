#!/bin/bash
set -e

users=${1:-10}
time=${2:-60}

#siege -c${users} -t${time}S https://prod--journal.elifesciences.org/content/4/e09560 # Homo Naledi, also 09561
siege -c${users} -t${time}S https://prod--journal.elifesciences.org/content/4/e09560/figures # Homo Naledi, also 09561
#siege -c${users} -t${time}S https://prod--journal.elifesciences.org/content/4/e10627
#siege -c${users} -t${time}S https://prod--journal.elifesciences.org/content/4/e10627/figures
#siege -c${users} -t${time}S https://prod--journal.elifesciences.org
