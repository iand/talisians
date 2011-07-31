import sys
import time

import twitter
import feedparser

#~ import httplib2

__version__ = "0.1"

USER_AGENT = "TalisiansSearch %s/Python %s" % (__version__, sys.version.replace("\n", ""))

TWITTER_KEY = "1016SmMf4C3DElicP5PkQ"
TWITTER_SECRET = "u8fZaeVjYWlPLq3QJVF90jedANfOVTR1uwYJhkzkThI"

def request(url, method="GET", body=None, headers=None):
  if headers is None:
    headers = {}
  
  headers["user-agent"] = USER_AGENT
  
  print "%s %s..." % (method, url),
  sys.stdout.flush()
  
  http = httplib2.Http("cache")
  response, content = http.request(url, method, body, headers)
  
  print "--> %d %s" % (response.status, response.reason)
  sys.stdout.flush()
  
  return response, content

class DeliciousSource(object):
  def get_items(self, user):
    feed = feedparser.parse("http://feeds.delicious.com/v2/rss/%s?count=15" % user)
    
    for entry in feed.entries:
      yield entry.link

class TwitterSource(object):
  def __init__(self):
    self.api = twitter.Api(consumer_key=TWITTER_KEY, consumer_secret=TWITTER_SECRET)
  
  def get_items(self, user):
    print self.api.VerifyCredentials()

sources = {
  DeliciousSource: [
    "kierdavis",
  ],
  
  TwitterSource: [
    "kierdavis",
  ],
}

def get_items():
  for cls, userlist in sources.items():
    src = cls()
    for user in userlist:
      links = list(src.get_items(user))
      print links
      
      time.sleep(1)

if __name__ == "__main__":
  get_items()
