from spectrum import logger, input, checks

LOGGER = logger.logger(__name__)

class JournalSearch():
    def __init__(self, journal):
        self._journal = journal

    def run(self):
        word = input.invented_word(3)
        LOGGER.info("Searching for %s", word)
        self._journal.search(word, count=None)

class JournalListing():
    def __init__(self, journal, path):
        self._journal = journal
        self._path = path

    def run(self)
        LOGGER.info("Loading %s", self._path)
        items = self._journal.listing(self._path)
        for i in items:
            self._journal.generic(i)
        # TODO: next page

        
JOURNAL_SEARCH = JournalSearch(checks.JOURNAL)
JOURNAL_LISTINGS = [
    JournalListing(checks.JOURNAL, '/subjects/neuroscience')
]
