# imports
import requests, pprint, time, threading

# constants
CREST_URL_ENDPOINTS		= "https://crest-tq.eveonline.com"
CREST_URL_MARKETTYPES		= "https://crest-tq.eveonline.com/market/types/"
CREST_URL_MARKETGROUPS		= "https://crest-tq.eveonline.com/market/groups/"
CREST_URL_PREFIX_HISTORY_FORGE	= "https://crest-tq.eveonline.com/market/10000002/history/?type="

FILE_MARKETTYPES	= "../txt/markettypes.txt"
FILE_MARKETGROUPS	= "../txt/marketgroups.txt"

CREST_RATE_LIMIT	= 150 # non-authorized requests per second; we'll stay below this
NUM_WORKER_THREADS	= 15 # slow calls to the CREST /history/ endpoint are parallelized

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
i = 0 # index of next element of marketTypes to process
j = 0 # number of elements processed so far in this bucket (one second)
empties = [] # types that contain empty history data, so index [-1] is out of bounds
lock = threading.Lock()

def resetLimit():
	global i, j
	while True :
		if i == len(marketTypes):
			return
		j = 0
		time.sleep(1)

def worker():
	global i, j
	td = threading.local() # thread-local data
	while True:
		if i == len(marketTypes):
			return
		if j == reqsPerSec:
			time.sleep(0.01)
			continue
		lock.acquire()
		if j == reqsPerSec:
			lock.release()
			time.sleep(0.01)
			continue
		# got the lock and we're not up against throttling constraints; proceed
		td.typePair	= marketTypes.items()[i] # locked access of i
		i += 1
		lock.release()
		td.typeKey 	= td.typePair[0]
		td.typeValue	= td.typePair[1]
		td.url = CREST_URL_PREFIX_HISTORY_FORGE + td.typeValue.crest_url
		td.history = requests.get(td.url).json()
		if len(td.history["items"]) < 2: # need two, not one, because we calc delta
			# print "Found insufficient history for type:", td.typeKey
			empties.append(td.typeKey)
			continue
		td.typeValue.px_x_vol = td.history["items"][-1]["avgPrice"] * td.history["items"][-1]["volume"]
		td.typeValue.px_x_vol_delta = (td.typeValue.px_x_vol
			- td.history["items"][-2]["avgPrice"] * td.history["items"][-2]["volume"])
		# print "Completed history query for:", td.typeKey

r = threading.Thread(target=resetLimit)
r.start()
workers = []
for k in range(NUM_WORKER_THREADS):
	t = threading.Thread(target=worker)
	workers.append(t)
	t.start()
	
# now wait for the workers to finish their queries
r.join()
for k in workers:
	k.join()

# print "Done!"

# given today's mkt vol and daily change, generate Javascript array for Treemap
'''
js_array_str  = "[\n"
js_array_str += "['Location', 'Parent', 'Market trade volume (size)', 'Market increase/decrease (color)'],\n"
js_array_str += "['Everything', null, 0, 0],\n"
for marketGroup, marketNode in marketGroups:
	if marketNode.parent == None:
		js_array_str += "['" + marketNode.name + "', 'Everything', 0, 0],\n"
	else:
		js_array_str += "['" + marketNode.name + "', '" + marketGroups[marketNode.parent].name + "', 0, 0],\n"
for marketType, marketNode in marketTypes:
	if marketNode.
'''
# save array in two locations: 1) datestamped archive copy 2) running "current" file for display
