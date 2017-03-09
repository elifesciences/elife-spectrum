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
    "/articles/correction",
    "/community",
    "/contact",
    "/for-the-press",
    "/resources",
    "/terms",
    #/who-we-work-with
]

LISTING_PATHS = [
    '/inside-elife',
    '/labs',
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

#    path: /content/{volume}/e{id}.bib
#    path: /content/{volume}/e{id}.ris
#    path: /articles/{type}

#path: /download/{uri}/{name}

#path: /about/people/{type}


@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", LISTING_PATHS)
def test_listings(path):
    items = checks.JOURNAL.listing(path)
    if len(items):
        checks.JOURNAL.generic(items[0])
#    path: /collections
# follow 1 link
#    path: /events/{id}
# follow 1 link
#    path: /inside-elife
# follow 1 link
#    path: /labs
# follow 1 link
#    path: /podcast
# follow 1 link
#    path: /subjects
# follow 1 link
#path: /inside-elife
# follow 1 link
#path: /articles/{type}
# follow 1 link

#    path: /interviews/{id}
# how do we get the link?

#    path: /search
