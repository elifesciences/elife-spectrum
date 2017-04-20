from spectrum import load, logger

LOGGER = logger.logger(__name__)

if __name__ == '__main__':
    while True:
        LOGGER.info("New run")
        load.JOURNAL_ALL.run()
