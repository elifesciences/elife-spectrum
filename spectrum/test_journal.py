"Tests that involve Journal pages that are not covered by other tests"
import pytest
from spectrum import checks, input

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.search
def test_homepage():
    links = checks.JOURNAL.homepage()
    if len(links):
        checks.JOURNAL.generic(links[0])

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.medium
@pytest.mark.search
def test_magazine():
    checks.JOURNAL.magazine()

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", checks.JOURNAL_GENERIC_PATHS)
def test_various_generic_pages(path):
    checks.JOURNAL.generic(path)

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", checks.JOURNAL_LISTING_PATHS)
def test_listings(path):
    items, _ = checks.JOURNAL.listing(path)
    if len(items):
        checks.JOURNAL.generic(items[0])

@pytest.mark.two
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", checks.JOURNAL_LISTING_OF_LISTING_PATHS)
def test_listings_of_listings(path):
    items = checks.JOURNAL.listing_of_listing(path)
    if len(items):
        checks.JOURNAL.generic(items[0])

@pytest.mark.two
@pytest.mark.journal_cms
def test_events():
    items, _ = checks.JOURNAL.listing('/events')
    if len(items):
        checks.JOURNAL.generic(items[0])

@pytest.mark.two
@pytest.mark.observer
def test_rss_feeds():
    recent_response = checks.JOURNAL.just_load('/rss/recent.xml')
    print recent_response.content
    ahead_response = checks.JOURNAL.just_load('/rss/ahead.xml')
    print ahead_response.content

# TODO: mark with `journal` all `two` to better isolate them
@pytest.mark.journal
@pytest.mark.profiles
def test_login():
    session = input.JOURNAL.session()
    session.login()
    session.logout()

#path: /interviews/{id}
# how do we get the link? navigate from /collections

#path: /content/{volume}/e{id}.bib
#path: /content/{volume}/e{id}.ris
#path: /download/{uri}/{name}
#path: /about/people/{type}
