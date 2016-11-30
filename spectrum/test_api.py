import pytest
from spectrum import checks

@pytest.mark.two
def test_list_based_apis():
    checks.API.labs_experiments()
    checks.API.subjects()
    checks.API.podcast_episodes()
    checks.API.people()
    #checks.API.medium_articles()
    checks.API.blog_articles()
    checks.API.events()
    checks.API.interviews()
    checks.API.collections()
