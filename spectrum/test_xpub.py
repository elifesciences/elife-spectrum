"Tests that involve Xpub integrations"
import pytest
from spectrum import input

@pytest.mark.journal
@pytest.mark.profiles
@pytest.mark.xpub
def test_submit_as_anonymous():
    session = input.JOURNAL.javascript_session()
    session.submit()
    # TODO: how to close the session? need a pytest fixture

