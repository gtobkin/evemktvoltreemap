# imports
import requests, pprint, time

# constants
CREST_URL_ENDPOINTS		= "https://crest-tq.eveonline.com"
CREST_URL_MARKETTYPES		= "https://crest-tq.eveonline.com/market/types/"
CREST_URL_MARKETGROUPS		= "https://crest-tq.eveonline.com/market/groups/"
CREST_URL_PREFIX_HISTORY_FORGE	= "https://crest-tq.eveonline.com/market/10000002/history/?type="

FILE_MARKETTYPES	= "../txt/markettypes.txt"
FILE_MARKETGROUPS	= "../txt/marketgroups.txt"

CREST_RATE_LIMIT	= 150 # non-authorized requests per second; we'll stay below this

# tree code
class MarketNode(object):
	def __init__(self):
		self.id			= None	# could be a type or group id
		self.name		= None
		self.crest_url		= None	# could be a type or group href
		self.parent		= None
		self.px_x_vol		= None
		self.px_x_vol_delta	= None

# pull API calls
endpoints = requests.get(CREST_URL_ENDPOINTS).json()

# verify our necessary API calls are supported
# just kidding - we can't, CCP doesn't list all of them
# ideally we'd verify that 'endpoints' contains the needed services
# and use the provided URLs from that instead of (possibly obsolete) constants

# pull market types and groups, store dicts in text files for human reference
marketTypesData = requests.get(CREST_URL_MARKETTYPES).json()
with open(FILE_MARKETTYPES, 'wt') as outfile:
	pprint.pprint(marketTypesData, stream=outfile)

marketGroupsData = requests.get(CREST_URL_MARKETGROUPS).json()
with open(FILE_MARKETGROUPS, 'wt') as outfile:
	pprint.pprint(marketGroupsData, stream=outfile)

# given market types and groups dicts, construct market tree
# first create all nodes, then create all parent links (once the parent is guaranteed to exist)
marketTypes = {}
for marketType in marketTypesData["items"]:
	node		= MarketNode()
	node.id		= marketType["id"]
	node.name	= marketType["type"]["name"]
	node.crest_url 	= marketType["type"]["href"]
	marketTypes[marketType["id"]] = node
marketGroups = {}
for marketGroup in marketGroupsData["items"]:
	node		= MarketNode()
	node.id		= marketGroup["id"]
	node.name	= marketGroup["name"]
	node.crest_url	= marketGroup["href"]
	marketGroups[marketGroup["id"]] = node
for marketType in marketTypesData["items"]:
	marketTypes[marketType["id"]].parent = marketGroups[marketType["marketGroup"]["id"]]
for marketGroup in marketGroupsData["items"]:
	if "parentGroup" in marketGroup: # not all market groups have parents
		marketGroups[marketGroup["id"]].parent = marketGroups[marketGroup["parentGroup"]["id"]]

# print len(marketTypes) 1000
# print len(marketGroups) 2157

# for each markettype, for yesterday + today, pull and calculate px*vol, and delta

reqsPerSec = round(CREST_RATE_LIMIT * 0.80)
# i = 0
for type in marketTypes:
	# no need for throttling, we're going at 2-3 requests per second, not 150
	# a possible optimization would be to parallelize the requests; maybe throttle then
	'''
	if i == reqsPerSec:
		time.sleep(1)
		i = 0
	'''
	url = CREST_URL_PREFIX_HISTORY_FORGE + marketTypes[type].crest_url
	history = requests.get(url).json()
	marketTypes[type].px_x_vol = history["items"][-1]["avgPrice"] * history["items"][-1]["volume"]
	marketTypes[type].px_x_vol_delta = (marketTypes[type].px_x_vol
		- history["items"][-2]["avgPrice"] * history["items"][-2]["volume"])
	# i += 1
	'''
	print i, "/", len(marketTypes)
	print "  NAME:", marketTypes[type].name
	print "  PX*V:", marketTypes[type].px_x_vol
	print "  DELT:", marketTypes[type].px_x_vol_delta
	'''

# given today's mkt vol and daily change, generate Javascript array for Treemap

# save array in two locations: 1) datestamped archive copy 2) running "current" file for display
