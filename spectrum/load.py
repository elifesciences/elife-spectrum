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

    def run(self):
        LOGGER.info("Loading %s", self._path)
        items = self._journal.listing(self._path)
        for item in items:
            LOGGER.info("Loading %s", item)
            self._journal.generic(item)
        # TODO: next page

class AllOf():
    def __init__(self, actions):
        self._actions = actions

    def run(self):
        # TODO: probability to weight actions
        for action in self._actions:
            action.run()

JOURNAL_SEARCH = JournalSearch(checks.JOURNAL)
JOURNAL_LISTINGS = [
    JournalListing(checks.JOURNAL, '/subjects/neuroscience')
]
JOURNAL_ALL = AllOf([JOURNAL_SEARCH]+JOURNAL_LISTINGS)
