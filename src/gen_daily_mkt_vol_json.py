# imports
import requests, pprint

# constants
CREST_URL_ENDPOINTS	= "https://crest-tq.eveonline.com"
CREST_URL_MARKETTYPES	= "https://crest-tq.eveonline.com/market/types/"
CREST_URL_MARKETGROUPS	= "https://crest-tq.eveonline.com/market/groups/"

FILE_MARKETTYPES	= "../txt/markettypes.txt"
FILE_MARKETGROUPS	= "../txt/marketgroups.txt"

# tree code
class MarketNode(object):
	def __init__(self):
		self.id			= None	# could be a market group id or a market type id
		self.crest_type_url	= None
		self.parent		= None

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

# given market types and groups JSON files, construct market tree
# first create all nodes, then create all parent links (once the parent is guaranteed to exist)
marketTypes = {}
for marketType in marketTypesData["items"]:
	node			= MarketNode()
	node.id			= marketType["id"]
	node.crest_type_url 	= marketType["type"]["href"]
	marketTypes[marketType["id"]] = node
marketGroups = {}
for marketGroup in marketGroupsData["items"]:
	node			= MarketNode()
	node.id			= marketGroup["id"]
	node.crest_type_url	= marketGroup["href"]
	marketGroups[marketGroup["id"]] = node
for marketType in marketTypesData["items"]:
	marketTypes[marketType["id"]].parent = marketGroups[marketType["marketGroup"]["id"]]
for marketGroup in marketGroupsData["items"]:
	if "parentGroup" in marketGroup: # not all market groups have parents
		marketGroups[marketGroup["id"]].parent = marketGroups[marketGroup["parentGroup"]["id"]]

# print len(marketTypes) 1000
# print len(marketGroups) 2157

# copy market tree; we now have trees for yesterday + today

# for each leaf, for yesterday + today, pull and calculate mkt vol

# trim leaves with 0 mkt vol both yesterday and today (is this really necessary?)

# for each leaf, calculate and store daily mkt vol change

# given today's mkt vol and daily change, generate Javascript array for Treemap

# save array in two locations: 1) datestamped archive copy 2) running "current" file for display
