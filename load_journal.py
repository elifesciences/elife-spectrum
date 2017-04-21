from spectrum import load

if __name__ == '__main__':
    while True:
        load.LOGGER.info("New run")
        try:
            load.JOURNAL_ALL.run()
        except (AssertionError, RuntimeError, UnrecoverableException, ValueError):
            load.LOGGER.exception()
