from random import randint
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

class JournalPage():
    def __init__(self, journal, path):
        self._journal = journal
        self._path = path

    def run(self):
        LOGGER.info("Loading fixed page %s", self._path)
        self._journal.generic(self._path)

# TODO: JournalHomepage

class AllOf():
    def __init__(self, actions):
        self._intervals = []
        start = 0
        for action, weight in actions:
            end = start + weight - 1
            self._intervals.append((start, end, action))
            start = end + 1
        self._total = end

    def run(self):
        choice = randint(0, self._total)
        action = None
        for (start, end, action) in self._intervals:
            if choice >= start and choice <= end:
                break
        if not action:
            raise RuntimeError("No action could be selected with choice %s: %s" % (choice, self._intervals))
        LOGGER.info("Selecting action %s", action)
        action.run()

JOURNAL_LISTINGS = [
    (JournalListing(checks.JOURNAL, '/subjects/neuroscience'), 2)
]
JOURNAL_PAGES = [
    (JournalPage(checks.JOURNAL, '/about'), 1)
]
JOURNAL_ALL = AllOf(
    [
        (JournalSearch(checks.JOURNAL), 4)
    ]
    +JOURNAL_LISTINGS
    +JOURNAL_PAGES
)
