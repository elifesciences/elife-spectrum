"Tests that go through Journal CMS and propagate content to the rest of the system"
from spectrum import input

def test_login():
    input.JOURNAL_CMS.login()

# TODO: mark with search and journal_cms
def test_content_type_propagates_to_other_services():
    # TODO: I fear this is too stateful
    input.JOURNAL_CMS.login()
    title = 'Spectrum blog article: %s' % input.invented_word()
    text = 'Lorem ipsum... %s' % title
    input.JOURNAL_CMS.create_blog_article(title=title, text=text)


