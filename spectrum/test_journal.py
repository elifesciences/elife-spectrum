"Tests that involve Journal pages that are not covered by other tests"
import pytest
from spectrum import checks

@pytest.mark.two
def test_various_pages():
    checks.JOURNAL.homepage()
    checks.JOURNAL.magazine()
