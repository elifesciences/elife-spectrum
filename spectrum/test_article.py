import pytest
from spectrum import generator
from spectrum import input
from spectrum import checks

@pytest.mark.parametrize("template_id", generator.all_stored_articles())
def test_article_flows_in_the_pipeline(template_id, article_id_filter):
    if article_id_filter:
        if template_id != article_id_filter:
            pytest.skip("Filtered out through the article_id_filter")

    article = generator.article_zip(template_id)
    input.PRODUCTION_BUCKET.upload(article.filename(), article.id())
    checks.EIF.of(id=article.id(), version=article.version())
    for each in article.figure_names():
        checks.IMAGES.of(id=article.id(), figure_name=each, version=article.version())
    if article.has_pdf():
        checks.PDF.of(id=article.id(), version=article.version())
    checks.WEBSITE.unpublished(id=article.id(), version=article.version())

