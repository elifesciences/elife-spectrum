from datetime import datetime
import pytest
from spectrum import articles
from spectrum import checks
from spectrum import input

DIGEST_ARTICLE_ID = '06847'

@pytest.mark.bot
@pytest.mark.digests
def test_digest_lifecycle(generate_digest, generate_article):
    digest = generate_digest(DIGEST_ARTICLE_ID)
    input.DIGESTS_BUCKET.upload(digest.filename(), id=digest.article_id())
    checks.BOT_EMAILS.wait_email(subject='Digest: Anonymous_%s' % digest.article_id())
    checks.BOT_INTERNAL_DIGEST_OUTBOX_DOC.of(id=digest.article_id())
    checks.BOT_INTERNAL_DIGEST_OUTBOX_JPG.of(id=digest.article_id())
    #checks.DIGEST_JPG_PUBLISHED_CDN_BUCKET.of(id=digest.article_id())

    article = generate_article(template_id=DIGEST_ARTICLE_ID, article_id=digest.article_id())
    ingestion_start = datetime.now()
    articles.ingest(article)
    articles.wait_for_publishable(article, ingestion_start)
    # TODO: not sure if the id has a prefix or is purely the article id
    #checks.API_SUPER_USER.digest(id=article.id())
