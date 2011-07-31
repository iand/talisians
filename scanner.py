import sys
import re
import time
import htmlentitydefs
import pickle

#~ import simplejson
import twitter
import feedparser

import httplib2
import tidy
from xml.etree import ElementTree as etree

__version__ = "0.1"

USER_AGENT = "TalisiansSearch %s/Python %s/Httplib2 %s" % (__version__, sys.version.replace("\n", ""), httplib2.__version__)

TWITTER_CON_KEY = "1016SmMf4C3DElicP5PkQ"
TWITTER_CON_SECRET = "u8fZaeVjYWlPLq3QJVF90jedANfOVTR1uwYJhkzkThI"
TWITTER_ACC_KEY = "83206564-GNnRwcCA5xM5hgrQ7qeu5cNZR0QMPfqVmoYBYpuYg"
TWITTER_ACC_SECRET = "OeLG9hwIKtDqIGHXqiZFjqarUbAR5YRoyW0c4yGzs"

#~ URL_REGEX = re.compile(r"""((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]+|(([^\s()<>]+)))*)|[^\s`!()[]{};:'".,<>?]))""", re.DOTALL)
URL_REGEX = re.compile(r"https?://[^\s)\]]+")

GRAVITY = 1.8

ENTITY = re.compile(r"&(\w+?);")
def ENTITY_REP(m):
  try:
    n = ord(htmlentitydefs.entitydefs[m.group(1)])
    return "&#%d;" % n
  except KeyError:
    return m.group(0)

#~ def request(url, method="GET", body=None, headers=None):
  #~ if headers is None:
    #~ headers = {}
  #~ 
  #~ headers["user-agent"] = USER_AGENT
  #~ 
  #~ print "%s %s..." % (method, url),
  #~ sys.stdout.flush()
  #~ 
  #~ http = httplib2.Http("cache")
  #~ response, content = http.request(url, method, body, headers)
  #~ 
  #~ print "--> %d %s" % (response.status, response.reason)
  #~ sys.stdout.flush()
  #~ 
  #~ return response, content

class FeedSource(object):
  def get_items(self, url):
    print "Fetching '%s'" % url
    feed = feedparser.parse(url)
    
    for entry in feed.entries:
      a, b, c = self._source_name(feed)
      yield entry.link, entry.title, time.mktime(entry.updated_parsed), a, b, c
  
  def _source_name(self, feed):
    return "Posted at", feed.feed.link, feed.feed.title

class DeliciousSource(FeedSource):
  def get_items(self, user):
    return FeedSource.get_items(self, "http://feeds.delicious.com/v2/rss/%s?count=30" % user)
  
  def _source_name(self, feed):
    return "Bookmarked by", feed.feed.link, feed.feed.title.split("/", 1)[1]

class PinboardSource(FeedSource):
  def get_items(self, user):
    return FeedSource.get_items(self, "http://feeds.pinboard.in/rss/u:%s/" % user)
  
  def _source_name(self, feed):
    return "Bookmarked by", feed.feed.link, feed.feed.title.split(None, 1)[1].strip("()")

class TwitterSource(object):
  def __init__(self):
    self.api = twitter.Api(
      consumer_key = TWITTER_CON_KEY,
      consumer_secret = TWITTER_CON_SECRET,
      access_token_key = TWITTER_ACC_KEY,
      access_token_secret = TWITTER_ACC_SECRET,
    )
  
  def get_items(self, user):
    print "Fetching user timeline for %s" % user
    try:
      statuses = self.api.GetUserTimeline(user, include_rts=True)
    except twitter.TwitterError, e:
      print "Twitter: %s" % str(e)
      return
    
    for status in statuses:
      #~ print "@@@@@@@@", status.text
      
      for m in URL_REGEX.finditer(status.text):
        #~ yield m.group(0), status.text, status.created_at_in_seconds
        yield m.group(0), None, status.created_at_in_seconds, "Tweeted by", "http://twitter.com/%s/status/%d" % (user, status.id), user

class Link(object):
  def __init__(self, url, text, time_added):
    self.url = url
    self.text = text
    self.time_added = time_added
    self.frequency = 0.0
    self.sources = {}
  
  def __getstate__(self):
    return self.url, self.text, self.time_added, self.frequency, self.sources
  
  def __setstate__(self, state):
    self.url, self.text, self.time_added, self.frequency, self.sources = state
  
  @property
  def age(self):
    "The age of the item, in hours"
    
    diff = time.time() - self.time_added
    return int(diff / 3600)
  
  @property
  def score(self):
    return ((self.frequency * 10.0) - 1.0) / ((self.age + 2.0) ** GRAVITY) * 10.0
  
  def get_sources_text(self, html=False):
    parts = []
    
    for where, l in self.sources.iteritems():
      s = where + " "
      
      i = 0
      for i, (link, text) in enumerate(l):
        if i != 0:
          if i == len(l) - 1:
            s += " and "
          
          else:
            s += ", "
        
        if not text:
          text = link
        
        if html:
          s += "<a href='%s'>%s</a>" % (link, text)
        else:
          s += text
      
      parts.append(s)
    
    return "\n".join(parts)
  
  def __repr__(self):
    return "<Link %s %r (freq = %d, age = %d hrs, score = %.2f)>" % (self.url, self.text, self.frequency, self.age, self.score)

sources = {
  FeedSource: [
    #~ "blog.iandavis.com/feed/",
  ],
  
  DeliciousSource: [
    "kierdavis",
    "ldodds",
  ],
  
  PinboardSource: [
    "iand",
  ],
  
  TwitterSource: [
    "kierdavis",
    "iand",
    "johnlsheridan",
    "ldodds",
    "mauvedeity",
    "mmmmmrob",
    "malcyL",
    "beobal",
  ],
}

def get_page_title(content):
  try:
    content = str(tidy.parseString(content, output_xhtml=True, add_xml_decl=True, indent=False, tidy_mark=False))
    content = ENTITY.sub(ENTITY_REP, content)
  
  #~ f = open("tmp.log", "w")
  #~ f.write(content)
  #~ f.close()
  
    root = etree.fromstring(content)
  
  except Exception, e:
    print "\tHTML Parser Error:", str(e)
    return ""
  
  head = root.find("{http://www.w3.org/1999/xhtml}head")
  title = head.find("{http://www.w3.org/1999/xhtml}title")
  titletext = title.text
  
  time.sleep(0.5)
  
  print "\tTitle:", titletext
  return titletext

def get_items():
  links = {}
  
  for cls, userlist in sources.items():
    src = cls()
    
    for user in userlist:
      print "Getting %s:%s" % (cls.__name__, user)
      
      for link, text, time_added, where, srcurl, srctext in src.get_items(user):
        try:
          http = httplib2.Http()
          response, content = http.request(link, headers={"user-agent": USER_AGENT})
        
        except Exception, e:
          print "\tHTTP Error: %s" % str(e)
          continue
        
        if "content-location" in response and link != response["content-location"]:
          print "Followed redirects from '%s'" % link,
          link = response["content-location"]
          print "to '%s'" % link
        
        if link in links:
          #~ print "===================== Found a dup!", link
          
          l = links[link]
          if time_added > l.time_added:
            l.time_added = time_added
          if not l.text:
            l.text = text
        
        else:
          if text is None:
            print "Getting page title for '%s'" % link
            text = get_page_title(content)
            if not text:
              continue
          
          l = links[link] = Link(link, text, time_added)
        
        l.frequency += 1.0
        
        if where not in l.sources:
          l.sources[where] = []
        
        k = (srcurl, srctext)
        if k not in l.sources[where]:
          l.sources[where].append(k)
        #~ l.sources[where].append(k)  # "Tweeted xxx times by xxx" ???
      
      time.sleep(1.0)
      print
  
  links = links.values()
  links.sort(key=lambda x: x.score, reverse=True)
  
  return links

def main():
  links = get_items()
  
  #~ jsonlist = []
  #~ for link in links:
    #~ jsonlist.append({
      #~ "url": link.url,
      #~ "text": link.text,
      #~ "time_added": link.time_added,
      #~ "frequency": link.frequency,
      #~ "sources": link.sources,
      #~ "age": link.age,
      #~ "score": link.score,
      #~ "sources_text": link.get_sources_text(False),
      #~ "sources_html": link.get_sources_text(True),
    #~ })
  
  f = open("links.pkl", "wb")
  pickle.dump(links, f)
  f.close()
  print "Wrote pickled links to links.pkl"
  
  f = open("web/index.html", "w")
  f.write(HTML_HEADER)
  
  for link in links[:15]:
    f.write("      <h3><a href='%s'>%s</a></h3>\n" % (link.url.encode("utf-8"), (link.text or link.url).encode("utf-8")))
    f.write("      <h5>%s</h5>\n" % (time.strftime("%a %d %b %Y, %I:%M %p", time.gmtime(link.time_added))))
    f.write("      <p>\n")
    f.write("        %s\n" % (link.get_sources_text(True).encode("utf-8").replace("\n", "\n<br>\n")))
    f.write("      </p>\n")
    f.write("      <hr/>\n")
    f.write("      \n")
  
  f.write(HTML_FOOTER)
  f.close()
  
  print "Wrote HTML to web/index.html"
  
  #~ print
  #~ print
  #~ for link in links:
    #~ print link
    #~ print link.get_sources_text(html=True)
    #~ print
    #~ 
  #~ 
  #~ print

HTML_HEADER = """
<!doctype html>
<!--[if lt IE 7 ]><html class="ie ie6" lang="en"> <![endif]-->
<!--[if IE 7 ]><html class="ie ie7" lang="en"> <![endif]-->
<!--[if IE 8 ]><html class="ie ie8" lang="en"> <![endif]-->
<!--[if (gte IE 9)|!(IE)]><!--><html lang="en"> <!--<![endif]-->
<head>

	<!-- Basic Page Needs
  ================================================== -->
	<meta charset="utf-8" />
	<title>Your Page Title Here :)</title>
	<meta name="description" content="">
	<meta name="author" content="">
	<!--[if lt IE 9]>
		<script src="http://html5shim.googlecode.com/svn/trunk/html5.js"></script>
	<![endif]-->
	
	<!-- Mobile Specific Metas
  ================================================== -->
	<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" /> 
	
	<!-- CSS
  ================================================== -->
	<link rel="stylesheet" href="stylesheets/base.css">
	<link rel="stylesheet" href="stylesheets/skeleton.css">
	<link rel="stylesheet" href="stylesheets/layout.css">
	
	<!-- Favicons
	================================================== -->
	<link rel="shortcut icon" href="images/favicon.ico">
	<link rel="apple-touch-icon" href="images/apple-touch-icon.png">
	<link rel="apple-touch-icon" sizes="72x72" href="images/apple-touch-icon-72x72.png" />
	<link rel="apple-touch-icon" sizes="114x114" href="images/apple-touch-icon-114x114.png" />
	
</head>
<body>

	<!-- Primary Page Layout
	================================================== -->
	
	<!-- Delete everything in this .container and get started on your own site! -->

	<div class="container">
    <div class="sixteen columns">
      <h1 class="remove-bottom" style="margin-top: 40px">Talisians</h1>
      <h4>Keep up to date on what's new!</h3>
      <hr/>
      
"""

HTML_FOOTER = """
    </div>
	</div><!-- container -->

		
		
		
		
	<!-- JS
	================================================== -->
	<script src="//ajax.googleapis.com/ajax/libs/jquery/1.5.1/jquery.js"></script>
	<script>window.jQuery || document.write("<script src='javascripts/jquery-1.5.1.min.js'>\x3C/script>")</script>
	<script src="javascripts/app.js"></script>
	
<!-- End Document
================================================== -->
</body>
</html>
"""

if __name__ == "__main__":
  main()
