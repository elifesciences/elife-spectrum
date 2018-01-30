from spectrum import load, checks
from sys import argv, exit
import requests

if __name__ == '__main__':
    if len(argv) < 2:
        load.LOGGER.error("No strategy specified. Usage: load.py STRATEGY [ITERATIONS]")
        exit(1)
    strategy = argv[1]
    load.LOGGER.info("Loading strategy %s", strategy)
    try:
        load_strategy = getattr(load, strategy)
    except AttributeError:
        load.LOGGER.error("Unknown strategy %s", strategy)
        exit(2)
    limit = load.Limit(argv[2] if len(argv) > 2 else None)
    load.LOGGER.info("Setting iterations limit %s", limit)

    limit.run(load_strategy)
