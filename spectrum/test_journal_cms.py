"Tests that go through Journal CMS and propagate content to the rest of the system"
from spectrum import input

def test_login():
    input.JOURNAL_CMS.login()
