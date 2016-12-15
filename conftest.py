import logging
import os
import sys

import pytest
from spectrum import generator
from spectrum import logger
# so that other processes run by xdist can still print
# http://stackoverflow.com/questions/27006884/pytest-xdist-without-capturing-output
# https://github.com/pytest-dev/pytest/issues/680
sys.stdout = sys.stderr

def pytest_addoption(parser):
    parser.addoption("--article-id",
                     action="store",
                     default=None,
                     help="pass an article id to filter only tests related to it")

@pytest.fixture
def article_id_filter(request):
    return request.config.getoption('--article-id')

@pytest.yield_fixture
#@pytest.fixture in pytest>=2.10
def generate_article():
    created_articles = []
    def from_template_id(template_id):
        article = generator.article_zip(str(template_id))
        created_articles.append(article)
        return article
    yield from_template_id
    _clean_all(created_articles)

@pytest.yield_fixture
def version_article():
    created_articles = []
    def from_original_article(original_article, new_version):
        article = original_article.new_version(version=new_version)
        created_articles.append(article)
        return article
    yield from_original_article
    _clean_all(created_articles)

@pytest.yield_fixture
def modify_article():
    created_articles = []
    def from_original_article(original_article, new_version=None, replacements=None):
        article = original_article.new_revision(version=new_version)
        article.replace_in_text(replacements if replacements else {})
        created_articles.append(article)
        return article
    yield from_original_article
    _clean_all(created_articles)

def _clean_all(created_articles):
    for article in created_articles:
        article.clean()

# pytest does not allow to read a cli argument globally, but
# only from a test or a fixture afaik
# so, workaround "trying hard to be an extensible tool and failing at it"
LOG_LEVEL = os.environ.get('SPECTRUM_LOG_LEVEL', 'INFO')
logger.set_logging_level(getattr(logging, LOG_LEVEL))
