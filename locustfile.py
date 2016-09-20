from locust import HttpLocust, TaskSet
from bs4 import BeautifulSoup

# http://demo--journal.elifesciences.org/content/4/e10627
def article(l):
    article_page = l.client.get("/content/4/e10627")
    soup = BeautifulSoup(article_page.content, 'html.parser')
    resources = []	
    for img in soup.find_all('img'):
        resources.append(img.get('src'))
    for script in soup.find_all('script'):
        if script.get('src'):
            resources.append(script.get('src'))
    for link in soup.find_all('link'):
        resources.append(link.get('href'))
    # TODO: https://github.com/locustio/locust/issues/198
    for r in resources:
        l.client.get(r)


class UserBehavior(TaskSet):
    tasks = {article:1}

    def on_start(self):
	pass

class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    #min_wait=5000
    #max_wait=9000

