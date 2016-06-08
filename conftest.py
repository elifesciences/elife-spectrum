import pytest

def pytest_addoption(parser):
    parser.addoption("--article-id", action="store", default=None,
            help="pass an article id to filter only tests related to it")

@pytest.fixture
def article_id_filter(request):
    return request.config.getoption('--article-id')
