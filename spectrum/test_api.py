"Tests that hit the API directly, checking the sanity of the JSON returned there"
import pytest
from spectrum import checks

@pytest.mark.two
def test_list_based_apis():
    checks.API.labs_experiments()
    checks.API.subjects()
    checks.API.podcast_episodes()
    checks.API.people()
    checks.API.medium_articles()
    checks.API.blog_articles()
    checks.API.events()
    checks.API.interviews()
    checks.API.collections()

@pytest.mark.two
def test_search():
    body = checks.API.search('inventednonexistentterm')
    assert body['total'] == 0, 'Searching for made up terms should not return results'
