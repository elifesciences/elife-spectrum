import pytest
from spectrum import checks

@pytest.mark.two
def test_integration_of_gateway():
    checks.API.labs_health()

@pytest.mark.two
def test_article_visibility():
    checks.JOURNAL.article(id=10627, volume=4) # Homo Naledi

