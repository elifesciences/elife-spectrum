import pytest
from spectrum import checks
from spectrum import input

SIMPLEST_ARTICLE_ID = 15893

@pytest.mark.bot
#@pytest.mark.digests
def test_digest_lifecycle(generate_digest):
    digest = generate_digest(SIMPLEST_ARTICLE_ID)
    input.DIGESTS_BUCKET.upload(digest.filename(), id=digest.article_id())
    checks.BOT_EMAILS.wait_email(subject='Digest: Anonymous_%s' % digest.article_id())
    checks.BOT_INTERNAL_DIGEST_OUTBOX_DOC.of(id=digest.article_id())
    checks.BOT_INTERNAL_DIGEST_OUTBOX_JPG.of(id=digest.article_id())
    #checks.DIGEST_JPG_PUBLISHED_CDN_BUCKET.of(id=digest.article_id())
