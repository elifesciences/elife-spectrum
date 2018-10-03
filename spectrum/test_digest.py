from datetime import datetime
import pytest
from spectrum import articles
from spectrum import checks
from spectrum import input

DIGEST_ARTICLE_ID = '00790'

@pytest.mark.bot
@pytest.mark.digests
def test_digest_lifecycle(generate_digest, generate_article, modify_article):
    # digest ingestion
    digest = generate_digest(DIGEST_ARTICLE_ID)
    input.DIGESTS_BUCKET.upload(digest.filename(), id=digest.article_id())
    checks.BOT_EMAILS.wait_email(subject='Digest: Anonymous_%s' % digest.article_id())
    checks.BOT_INTERNAL_DIGEST_OUTBOX_DOC.of(id=digest.article_id())
    checks.BOT_INTERNAL_DIGEST_OUTBOX_JPG.of(id=digest.article_id())
    #checks.DIGEST_JPG_PUBLISHED_CDN_BUCKET.of(id=digest.article_id())

    # article ingestion
    article = generate_article(template_id=DIGEST_ARTICLE_ID, article_id=digest.article_id())
    ingestion_start = datetime.now()
    articles.ingest(article)
    run = articles.wait_for_publishable(article, ingestion_start)
    checks.API_SUPER_USER.digest(id=article.id())

    # article publishing
    articles.publish(article, run)
    checks.API.wait_digest(id=article.id())
    checks.JOURNAL.digest(id=article.id())

    # silent correction after publication
    silently_corrected_article = modify_article(article, replacements={'outcompetes': 'OUTCOMPETES'})
    articles.feed_silent_correction(silently_corrected_article)
    checks.API.wait_article(id=article.id(), title='Fungal effector Ecp6 OUTCOMPETES host immune receptor for chitin binding through intrachain LysM dimerization')
