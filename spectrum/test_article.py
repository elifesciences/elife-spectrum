import pytest
from spectrum import generator
from spectrum import input
from spectrum import checks

@pytest.mark.parametrize("template_id", generator.all_stored_articles())
def test_article_flows_in_the_pipeline(template_id):
    article = generator.article_zip(template_id)
    input.PRODUCTION_BUCKET.upload(article.filename())
    checks.EIF.of(id=article.id())
    checks.WEBSITE.unpublished(id=article.id())
    for each in article.figure_names():
        checks.IMAGES.of(id=article.id(), figure_name=each)
    if article.has_pdf():
        checks.PDF.of(id=article.id())

