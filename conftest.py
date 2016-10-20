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
def generate_article(version=1):
    created_articles = []
    def from_template_id(template_id):
        article = generator.article_zip(template_id, version=version)
        created_articles.append(article)
        return article
    yield from_template_id
    for article in created_articles:
        article.clean()

def version_article(original_article, new_version):
    created_articles = []
    def from_original_article(original_article):
        article = original_article.new_version(version=new_version)
        created_articles.append(article)
        return article
    yield from_original_article
    for article in created_articles:
        article.clean()
