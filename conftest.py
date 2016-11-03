import sys

import pytest
from spectrum import generator
from spectrum import logger

# so that other processes run by xdist can still print
# http://stackoverflow.com/questions/27006884/pytest-xdist-without-capturing-output
# https://github.com/pytest-dev/pytest/issues/680
sys.stdout = sys.stderr

def pytest_addoption(parser):
    parser.addoption("--article-id", action="store", default=None,
            help="pass an article id to filter only tests related to it")

@pytest.fixture
def article_id_filter(request):
    return request.config.getoption('--article-id')

@pytest.yield_fixture
#@pytest.fixture in pytest>=2.10
def generate_article():
    created_articles = []
    def from_template_id(template_id, version=1):
        article = generator.article_zip(str(template_id), version=version)
        created_articles.append(article)
        return article
    yield from_template_id
    for article in created_articles:
        article.clean()

@pytest.yield_fixture
def version_article():
    created_articles = []
    def from_original_article(original_article, new_version, version_number_prefix='r'):
        article = original_article.new_version(version=new_version, version_number_prefix=version_number_prefix)
        created_articles.append(article)
        return article
    yield from_original_article
    for article in created_articles:
        article.clean()
