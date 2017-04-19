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
        self._queue = [path]

    def run(self):
        path = self._queue.pop()
        LOGGER.info("Loading listing %s", path)
        items, links = self._journal.listing(path)
        for item in items:
            LOGGER.info("Loading %s", item)
            self._journal.generic(item)
        for link in links:
            self._queue.insert(0, link)

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
