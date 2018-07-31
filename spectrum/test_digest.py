import pytest
from spectrum import generator
from spectrum import input

SIMPLEST_ARTICLE_ID = 15893

@pytest.mark.bot
#@pytest.mark.digests
def test_digest_lifecycle():
    digest = generator.digest_doc(SIMPLEST_ARTICLE_ID)
    input.DIGESTS_BUCKET.upload(digest.filename(), id=digest.article_id())
