"Tests that involve Xpub integrations"
import pytest
from spectrum import input

@pytest.mark.journal
@pytest.mark.profiles
@pytest.mark.xpub
def test_submit_as_anonymous():
    journal_session = input.JOURNAL.javascript_session()
    xpub_session = journal_session.submit()
    xpub_session.login()
    # TODO: how to close the session (driver)? need a pytest fixture

