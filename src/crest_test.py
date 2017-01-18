import requests, pprint
# print out all endpoints
url = "https://crest-tq.eveonline.com"
json = requests.get(url).json()
pp = pprint.PrettyPrinter(indent=4, depth=6)
pp.pprint(json)

# print out trit market history specifically
url = "https://crest-tq.eveonline.com/market/10000002/history/?type=https://crest-tq.eveonline.com/inventory/types/34/"
json = requests.get(url).json()
pp = pprint.PrettyPrinter(indent=4, depth=6)
pp.pprint(json)
exit()
