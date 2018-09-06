"Tests that go through Journal CMS and propagate content to the rest of the system"
import pytest
import requests
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
    title = 'Spectrum annual report: %s' % invented_word
    year = 2018
    journal_cms_session.create_annual_report(title=title, year=year, url='https://2018.elifesciences.org')
    result = checks.API.wait_search(invented_word)
    assert result['total'] == 1, "There should only be one result containing this word"
    assert result['items'][0]['title'] == title, "The title of the annual report found through search is incorrect"
    id = result['items'][0]['year']
    annual_report = checks.API.annual_report(id)
    assert annual_report['year'] == year, "The year of the annual report is incorrect"

