"Tests that involve Journal pages that are not covered by other tests"
import pytest
from spectrum import checks

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
def test_various_generic_pages():
    checks.JOURNAL.generic("/about")
    checks.JOURNAL.generic("/alerts")
    checks.JOURNAL.generic("/archive/2016")
    checks.JOURNAL.generic("/community")
    checks.JOURNAL.generic("/contact")
    checks.JOURNAL.generic("/for-the-press")
    checks.JOURNAL.generic("/resources")
    checks.JOURNAL.generic("/terms")

#    path: /content/{volume}/e{id}.bib
#    path: /content/{volume}/e{id}.ris
#    path: /articles/{type}

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

#    path: /interviews/{id}
# how do we get the link?

#    path: /search
