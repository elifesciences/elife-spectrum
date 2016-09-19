from locust import HttpLocust, TaskSet
from bs4 import BeautifulSoup
import gevent

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

def stats_persist():
    while True:
        from locust.runners import locust_runner
        print "stats_persist"
        print locust_runner
        store_stats('/tmp/locust-stats.log', locust_runner.request_stats)
        gevent.sleep(2)

def store_stats(filename, stats):
    with open(filename, "w") as f:
        f.write("path,method,num_requests,num_failures,min_response_time,max_response_time,avg_response_time\n")
        for k in stats:
            r = stats[k]
            f.write("%s,%s,%d,%d,%d,%d,%d\n" % (r.name,r.method,r.num_requests,r.num_failures,r.min_response_time,r.max_response_time,r.avg_response_time));
    
gevent.spawn(stats_persist) 
