import pytest
from spectrum import generator
from spectrum import input
from spectrum import checks

@pytest.mark.parametrize("template_id", generator.all_stored_articles())
def test_uploaded_article_gets_transformed_into_eif(template_id):
    article = generator.article_zip(template_id)
    input.production_bucket.upload(article.filename())
    checks.eif.of(id=article.id())
    checks.website.unpublished(id=article.id())

