import requests
url = "http://eve-marketdata.com/api/item_history2.json?char_name=demo2&region_ids=10000002&type_ids=34,456"
#print requests.get(url).json()
data = requests.get(url).json()
print data["emd"]["name"]
print "Everything from EMD:"
print data
print "\n\n"
#url = "http://api.eve-central.com/api/marketstat/json?typeid=34&typeid=35&regionlimit=10000002"
url = "http://api.eve-central.com/api/marketstat/json?typeid=35940&regionlimit=10000002"
data = requests.get(url).json()
print data[0]["sell"]
print "Everything from EC:"
print data
print "\n\n"
exit()


import urllib, json, simplejson
from urllib import FancyURLopener
class MyOpener(FancyURLopener):
	version = 'My new User-Agent'
print MyOpener.version
url = "http://eve-marketdata.com/api/item_history2.json?char_name=demo2&region_ids=10000002&type_ids=34,456"
myopener = MyOpener()
page = myopener.open(url)
print page.read()
data = simplejson.load(page)
#data = json.loads(page.read())
#response = urllib.urlopen(url)
#print url
#print response
#print response.read()
#data = json.load(response)
#print data
