"Tests that involve Journal pages that are not covered by other tests"
import pytest
from spectrum import checks

GENERIC_PATHS = [
    "/about",
    "/about/early-career",
    "/about/innovation",
    "/about/openness",
    "/about/peer-review",
    "/alerts",
    "/annual-reports",
    "/archive/2016",
    "/community",
    "/contact",
    "/for-the-press",
    "/resources",
    "/terms",
    #/who-we-work-with
]

LISTING_PATHS = [
    '/articles/correction',
    '/collections',
    '/events',
    '/inside-elife',
    '/labs',
    '/podcast',
    '/subjects',
]

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.search
def test_homepage():
    checks.JOURNAL.homepage()

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.medium
@pytest.mark.search
def test_magazine():
    checks.JOURNAL.magazine()

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", GENERIC_PATHS)
def test_various_generic_pages(path):
    checks.JOURNAL.generic(path)


@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", LISTING_PATHS)
def test_listings(path):
    items = checks.JOURNAL.listing(path)
    if len(items):
        checks.JOURNAL.generic(items[0])

#path: /interviews/{id}
# how do we get the link? navigate from /collections

#path: /content/{volume}/e{id}.bib
#path: /content/{volume}/e{id}.ris
#path: /download/{uri}/{name}
#path: /about/people/{type}
