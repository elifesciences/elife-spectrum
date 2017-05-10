from spectrum import load, checks
from sys import argv
import requests

if __name__ == '__main__':
    if len(argv) >= 2:
        limit = int(argv[1])
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
            load.JOURNAL_ALL.run()
        except (AssertionError, RuntimeError, ValueError, checks.UnrecoverableError, requests.exceptions.ConnectionError) as e:
            load.LOGGER.exception("Error in loading a journal page (%s)", e.message)
        iterations = iterations + 1

