"Tests that go through Journal CMS and propagate content to the rest of the system"
import pytest
from spectrum import input
from spectrum import checks

@pytest.mark.journal_cms
def test_login():
    input.JOURNAL_CMS.login()

@pytest.mark.journal_cms
@pytest.mark.search
def test_content_type_propagates_to_other_services():
    journal_cms_session = input.JOURNAL_CMS.login()

    invented_word = input.invented_word()
    title = 'Spectrum blog article: %s' % invented_word
    text = 'Lorem ipsum... %s' % title
    journal_cms_session.create_job_advert(title=title, text=text)
    result = checks.API.wait_search(invented_word)
    assert result['total'] == 1, "There should only be one result containing this word"
    assert result['items'][0]['title'] == title, "The title of the job advert found through search is incorrect"

