"Tests that involve Journal pages that are not covered by other tests"
import pytest
from spectrum import checks, input

MAGIC_ORCID = '0000-0002-1825-0097'

@pytest.mark.two
@pytest.mark.journal
@pytest.mark.journal_cms
@pytest.mark.search
def test_homepage():
    links = checks.JOURNAL.homepage()
    if len(links):
        checks.JOURNAL.generic(links[0])

@pytest.mark.two
@pytest.mark.journal
@pytest.mark.journal_cms
@pytest.mark.medium
@pytest.mark.search
def test_magazine():
    checks.JOURNAL.magazine()

@pytest.mark.two
@pytest.mark.journal
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", checks.JOURNAL_GENERIC_PATHS)
def test_various_generic_pages(path):
    checks.JOURNAL.generic(path)

@pytest.mark.two
@pytest.mark.journal
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", checks.JOURNAL_LISTING_PATHS)
def test_listings(path):
    items, _ = checks.JOURNAL.listing(path)
    if len(items):
        checks.JOURNAL.generic(items[0])

@pytest.mark.two
@pytest.mark.journal
@pytest.mark.journal_cms
@pytest.mark.parametrize("path", checks.JOURNAL_LISTING_OF_LISTING_PATHS)
def test_listings_of_listings(path):
    items = checks.JOURNAL.listing_of_listing(path)
    if len(items):
        checks.JOURNAL.generic(items[0])

@pytest.mark.two
@pytest.mark.journal
@pytest.mark.journal_cms
def test_events():
    items, _ = checks.JOURNAL.listing('/events')
    if len(items):
        checks.JOURNAL.generic(items[0])

@pytest.mark.two
@pytest.mark.journal
@pytest.mark.observer
def test_rss_feeds():
    recent_response = checks.JOURNAL.just_load('/rss/recent.xml')
    print recent_response.content
    ahead_response = checks.JOURNAL.just_load('/rss/ahead.xml')
    print ahead_response.content

@pytest.mark.journal
@pytest.mark.profiles
@pytest.mark.annotations
def test_logging_in_and_out():
    session = input.JOURNAL.session()
    session.enable_feature_flag()
    original = '/about'
    session.check(original)
    returned_to = session.login(referer=original)
    assert '/about' in returned_to.url, "Did not come back to the original page after log in"

    session.logout()

@pytest.mark.journal
@pytest.mark.profiles
@pytest.mark.annotations
def test_logged_in_profile():
    session = input.JOURNAL.session()
    session.enable_feature_flag()
    session.login()

    id = _find_profile_id_by_orcid(MAGIC_ORCID)
    session.check('/profiles/%s' % id)

@pytest.mark.journal
@pytest.mark.profiles
@pytest.mark.annotations
def test_public_profile():
    profile_creation_session = input.JOURNAL.session()
    profile_creation_session.enable_feature_flag()
    profile_creation_session.login()

    anonymous_session = input.JOURNAL.session()
    anonymous_session.enable_feature_flag()
    profile_id = _find_profile_id_by_orcid(MAGIC_ORCID)

    anonymous_session.check('/profiles/%s' % profile_id)

#path: /interviews/{id}
# how do we get the link? navigate from /collections

#path: /content/{volume}/e{id}.bib
#path: /content/{volume}/e{id}.ris
#path: /download/{uri}/{name}
#path: /about/people/{type}

def _find_profile_id_by_orcid(orcid):
    # no pagination needed so far
    profiles = checks.API.profiles()['items']
    for profile_snippet in profiles:
        # magic ORCID used by orcid-dummy
        if profile_snippet['orcid'] == orcid:
            return profile_snippet['id']
    assert id is not None, "We didn't find the profile for the test user %s in %s" % (orcid, profiles)

