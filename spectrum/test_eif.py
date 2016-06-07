import pytest
from spectrum import generator
from spectrum import input
from spectrum import checks

def all_stored_articles():
    return ["15853", "15893", "15600"]

@pytest.mark.parametrize("article", all_stored_articles())
def test_uploaded_article_gets_transformed_into_eif(article):
    article = generator.article_zip()
    input.production_bucket.upload(article.filename())
    checks.eif.of(id=article.id())
    checks.website.unpublished(id=article.id())

