"Tests that involve Xpub integrations"
import pytest
from spectrum import input

@pytest.mark.journal
@pytest.mark.profiles
@pytest.mark.xpub
def test_initial_submission(get_selenium_driver):
    journal_session = input.JOURNAL.javascript_session(get_selenium_driver())
    xpub_session = journal_session.submit()
    xpub_session.login()
    author_page = xpub_session.dashboard().create_initial_submission()
    author_page.next()