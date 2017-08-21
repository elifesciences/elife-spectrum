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
    if len(argv) >= 3:
        limit = int(argv[2])
        load.LOGGER.info("Setting iterations limit %s", limit)
    else:
        limit = None
        load.LOGGER.info("No limit set")

    iterations = 0
    while True:
        if limit is not None:
            if iterations >= limit:
                load.LOGGER.info("Stopping at %s iterations limit", limit)
                break
        load.LOGGER.info("New iteration")
        try:
            load_strategy.run()
        except (AssertionError, RuntimeError, ValueError, checks.UnrecoverableError, requests.exceptions.ConnectionError) as e:
            load.LOGGER.exception("Error in loading (%s)", e.message)
        iterations = iterations + 1

