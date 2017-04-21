from spectrum import load

if __name__ == '__main__':
    while True:
        load.LOGGER.info("New run")
        load.JOURNAL_ALL.run()
