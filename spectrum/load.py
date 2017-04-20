from random import randint
from spectrum import logger, input, checks

LOGGER = logger.logger(__name__)

class Queue():
    def __init__(self, contents = None):
        self._contents = contents if contents else []
        self._seed = self._contents

    def dequeue(self):
        path = self._contents.pop()
        LOGGER.debug("Dequeuing %s", path)
        return path

    def enqueue(self, path_to_visit):
        LOGGER.debug("Enqueuing %s", path_to_visit)
        self._contents.insert(0, path_to_visit)

    def restart_if_empty(self):
        if len(self._contents) == 0:
            self._contents = self._seed

    def __len__(self):
        return len(self._contents)

class JournalSearch():
    def __init__(self, journal, length=3):
        self._journal = journal
        self._length = length
        self._results = Queue()

    def run(self):
        if len(self._results):
            result = self._results.dequeue()
            LOGGER.info("Loading search result %s", result)
            self._journal.generic(result)
        else:
            word = input.invented_word(self._length)
            LOGGER.info("Searching for %s", word)
            results = self._journal.search(word, count=None)
            # TODO: Queue.enqueue_all
            for result in results:
                self._results.enqueue(result)

    def __str__(self):
        return "JournalSearch(length=%s)" % self._length

class JournalListing():
    def __init__(self, journal, path):
        self._journal = journal
        self._path = path
        self._pages = Queue([path])
        self._items = Queue()

    def run(self):
        if len(self._items):
            item = self._items.dequeue()
            LOGGER.info("Loading listing item %s", item)
            self._journal.generic(item)
        else:
            path = self._pages.dequeue()
            LOGGER.info("Loading listing page %s", path)
            items, links = self._journal.listing(path)
            for item in items:
                self._items.enqueue(item)
            for link in links:
                self._pages.enqueue(link)
        # TODO: really necessary?
        self._pages.restart_if_empty()

    def __str__(self):
        return "JournalListing(%s, pages queue length %s, items queue length %s)" % (self._path, len(self._pages), len(self._items))

class JournalListingOfListing():
    def __init__(self, journal, path):
        self._journal = journal
        self._path = path
        self._listings = Queue()

    def run(self):
        if len(self._listings):
            listing = self._listings.dequeue()
            listing.run()
            self._listings.enqueue(listing)
        else:
            LOGGER.info("Loading listing of listing %s", self._path)
            for listing in self._journal.listing_of_listing(self._path):
                self._listings.enqueue(JournalListing(self._journal, listing))

    def __str__(self):
        return "JournalListingOfListing(%s, listings queue length %s)" % (self._path, len(self._listings))

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
        self._links = Queue()

    def run(self):
        if len(self._links):
            link = self._links.dequeue()
            LOGGER.info("Loading link %s", link)
            self._journal.generic(link)
        else:
            LOGGER.info("Loading homepage /")
            links = self._journal.homepage()
            for link in links:
                self._links.enqueue(link)

    def __str__(self):
        return "JournalHomepage(links queue length %s)" % len(self._links)

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
    (JournalListingOfListing(JOURNAL, p), 2) for p in checks.JOURNAL_LISTING_OF_LISTING_PATHS
]
JOURNAL_PAGES = [
    (JournalPage(JOURNAL, p), 1)
    for p in checks.JOURNAL_GENERIC_PATHS
]
JOURNAL_ALL = AllOf(
    [
        (JournalSearch(JOURNAL), 8),
        #(JournalHomepage(JOURNAL), 8),
    ]
    #+JOURNAL_LISTINGS
    #+JOURNAL_LISTINGS_OF_LISTINGS
    #+JOURNAL_PAGES
)
