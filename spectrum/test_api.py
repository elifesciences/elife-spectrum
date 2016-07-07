import pytest
from spectrum import checks

def test_article_flows_in_the_pipeline():
    checks.API.labs_health()

