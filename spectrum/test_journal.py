import pytest
from spectrum import checks

@pytest.mark.two
def test_various_pages():
    checks.JOURNAL.homepage()
