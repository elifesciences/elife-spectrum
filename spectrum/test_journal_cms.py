"Tests that go through Journal CMS and propagate content to the rest of the system"
from spectrum import input
from spectrum import checks

@pytest.mark.journal_cms
def test_login():
    input.JOURNAL_CMS.login()

@pytest.mark.journal_cms
@pytest.mark.search
def test_content_type_propagates_to_other_services():
    # TODO: I fear this is too stateful
    input.JOURNAL_CMS.login()

    invented_word = input.invented_word()
    title = 'Spectrum blog article: %s' % invented_word
    text = 'Lorem ipsum... %s' % title
    input.JOURNAL_CMS.create_blog_article(title=title, text=text)
    result = checks.API.wait_search(invented_word)
    assert result['total'] == 1, "There should only be one result containing this word"
    assert result['items'][0]['title'] == title, "The title of the blog article found through search is incorrect"


