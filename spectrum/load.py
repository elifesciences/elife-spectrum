from random import randint
from spectrum import logger, input, checks

LOGGER = logger.logger(__name__)

class JournalSearch():
    def __init__(self, journal, length=3):
        self._journal = journal
        self._length = length

    def run(self):
        word = input.invented_word(self._length)
        LOGGER.info("Searching for %s", word)
        self._journal.search(word, count=None)

    def __str__(self):
        return "JournalSearch(length=%s)" % self._length

class JournalListing():
    def __init__(self, journal, path):
        self._journal = journal
        self._path = path
        self._queue = [path]

    def run(self):
        path = self._dequeue()
        LOGGER.info("Loading listing %s", path)
        items, links = self._journal.listing(path)
        for item in items:
            LOGGER.info("Loading item %s", item)
            self._journal.generic(item)
        for link in links:
            self._enqueue(link)
        self._restart_if_empty()

    def _dequeue(self):
        path = self._queue.pop()
        LOGGER.debug("Dequeuing %s", path)
        return path

    def _enqueue(self, path_to_visit):
        LOGGER.debug("Enqueuing %s", path_to_visit)
        self._queue.insert(0, path_to_visit)

    def _restart_if_empty(self):
        if len(self._queue) == 0:
            self._queue.insert(0, self._path)

    def __str__(self):
        return "JournalListing(%s, queue length %s)" % (self._path, len(self._queue))

class JournalListingOfListing():
    def __init__(self, journal, path):
        self._journal = journal
        self._path = path

    def run(self):
        LOGGER.info("Loading listing of listing %s", self._path)
        listings = AllOf([
            (JournalListing(self._journal, item), 1)
            for item in self._journal.listing_of_listing(self._path)
        ])
        listings.run()

    def __str__(self):
        return "JournalListingOfListing(%s)" % self._path

class JournalPage():
    def __init__(self, journal, path):
        self._journal = journal
        self._path = path

    def run(self):
        LOGGER.info("Loading fixed page %s", self._path)
        self._journal.generic(self._path)

    def __str__(self):
        return "JournalPage(%s)" % self._path

class JournalHomepage():
    def __init__(self, journal):
        self._journal = journal

    def run(self):
        LOGGER.info("Loading homepage /")
        links = self._journal.homepage()
        for link in links:
            LOGGER.info("Loading link %s", link)
            self._journal.generic(link)

    def __str__(self):
        return "JournalHomepage()"

class AllOf():
    def __init__(self, actions):
        "every element of actions is a tuple (action, weight) where action has a run() method"
        self._intervals = []
        start = 0
        assert len(actions) > 0, "Cannot create AllOf with an empty list of actions"
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

JOURNAL = checks.JOURNAL.with_resource_checking_method('get')
JOURNAL_LISTINGS = [
    (JournalListing(JOURNAL, p), 2) for p in checks.JOURNAL_LISTING_PATHS
]
JOURNAL_LISTINGS_OF_LISTINGS = [
    (JournalListingOfListing(JOURNAL, p), 200) for p in checks.JOURNAL_LISTING_OF_LISTING_PATHS
]
JOURNAL_PAGES = [
    (JournalPage(JOURNAL, p), 1)
    for p in checks.JOURNAL_GENERIC_PATHS
]
JOURNAL_ALL = AllOf(
    [
        (JournalSearch(JOURNAL), 8),
        (JournalHomepage(JOURNAL), 800),
    ]
    +JOURNAL_LISTINGS
    +JOURNAL_LISTINGS_OF_LISTINGS
    +JOURNAL_PAGES
)
