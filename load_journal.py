from spectrum import load, checks

if __name__ == '__main__':
    while True:
        load.LOGGER.info("New run")
        try:
            load.JOURNAL_ALL.run()
        except (AssertionError, RuntimeError, ValueError, checks.UnrecoverableError):
            load.LOGGER.exception("Error in loading a journal page")
