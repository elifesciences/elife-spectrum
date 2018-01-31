from argparse import ArgumentParser
from spectrum import load, checks
from sys import argv, exit
import requests

if __name__ == '__main__':
    parser = ArgumentParser(description="Load tests Journal")
    parser.add_argument('strategy', type=str, help='Strategy to use e.g. JOURNAL_ALL')
    parser.add_argument('--limit', type=int, default=None, help='The maximum number of checks to make before stopping')
    arguments = parser.parse_args()
    load.LOGGER.info("Loading strategy %s", arguments.strategy)
    try:
        load_strategy = getattr(load, arguments.strategy)
    except AttributeError:
        load.LOGGER.error("Unknown strategy %s", arguments.strategy)
        exit(2)
    limit = load.Limit(arguments.limit)
    load.LOGGER.info("Setting iterations limit %s", limit)

    limit.run(load_strategy)
