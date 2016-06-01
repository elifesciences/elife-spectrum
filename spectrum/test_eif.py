import unittest
from spectrum import generator
from spectrum import input
from spectrum import checks

class TestPublishing(unittest.TestCase):
    def test_uploaded_article_gets_transformed_into_eif(self):
        article = generator.article_zip()
        input.production_bucket.upload(article.filename())
        checks.eif.of(id=article.id())

    def test_another_larger_article_gets_transformed_into_eif(self):
        article = generator.article_zip(template_id=15853)


