"Tests that hit the API directly, checking the sanity of the JSON returned there"
import pytest
from spectrum import checks

@pytest.mark.two
@pytest.mark.journal_cms
def test_list_based_apis_journal_cms():
    checks.API.labs_posts()
    checks.API.subjects()
    checks.API.podcast_episodes()
    checks.API.people()
    checks.API.blog_articles()
    checks.API.events()
    checks.API.interviews()
    checks.API.collections()

@pytest.mark.profiles
def test_list_based_apis_profiles():
    checks.API.profiles()

@pytest.mark.skip(reason="ORCID referer redirect behaviour has changed")
@pytest.mark.annotations
def test_list_based_apis_annotations():
    any_profile = 'jcarberry'
    public_version = checks.API.annotations(any_profile)
    super_user_version = checks.API_SUPER_USER.annotations(any_profile, access='restricted')
    assert super_user_version['total'] > public_version['total']

@pytest.mark.digests
def test_list_based_apis_digests():
    checks.API.digests()

@pytest.mark.two
@pytest.mark.search
def test_search():
    body = checks.API.search('inventednonexistentterm')
    assert body['total'] == 0, 'Searching for made up terms should not return results'
