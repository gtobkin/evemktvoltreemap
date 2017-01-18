import requests, pprint
# print out all endpoints
url = "https://crest-tq.eveonline.com/market/groups/"
json = requests.get(url).json()
pp = pprint.PrettyPrinter(indent=4, depth=6)
pp.pprint(json)
