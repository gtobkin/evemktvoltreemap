# imports
import requests, datetime, pprint, time, threading, shutil

# constants
CREST_URL_ENDPOINTS		= "https://crest-tq.eveonline.com"
CREST_URL_TIME			= "https://crest-tq.eveonline.com/time/"
CREST_URL_MARKETTYPES		= "https://crest-tq.eveonline.com/market/types/"
CREST_URL_MARKETGROUPS		= "https://crest-tq.eveonline.com/market/groups/"
CREST_URL_PREFIX_HISTORY_FORGE	= "https://crest-tq.eveonline.com/market/10000002/history/?type="

FILE_MARKETTYPES	= "../txt/markettypes.txt"
FILE_MARKETGROUPS	= "../txt/marketgroups.txt"
FILE_PREFIX_OUTPUT	= "../out/mkt_vol_array_"

CREST_RATE_LIMIT	= 150 # non-authorized requests per second; we'll stay below this
NUM_WORKER_THREADS	= 20 # slow calls to the CREST /history/ endpoint are parallelized
HIST_CALL_PRINT_MOD	= 100 # print out a status update every n'th call to the /history endpoint

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

# determine current EVE date
response = requests.get(CREST_URL_TIME).json()
currentDateStr = response["time"][0:10]
# use datetime operations to handle month rollover, leap days, etc.
currentDate = datetime.date(int(currentDateStr[0:4]), int(currentDateStr[5:7]), int(currentDateStr[8:10]))
oneDay = datetime.timedelta(days=1)
targetDate = currentDate - oneDay
targetPrevDate = targetDate - oneDay # for use in calculating px_x_vol_delta
targetDateStr = str(targetDate)
targetPrevDateStr = str(targetPrevDate)

print "Current EVE date:           ", currentDateStr
print "Generating treemap for date:", targetDateStr
print "Deltas from prior date:     ", targetPrevDateStr
print ""

# pull market types and groups, store dicts in text files for human reference
page = 1
response = requests.get(CREST_URL_MARKETTYPES).json()
marketTypesData = response["items"]
pageCount = response["pageCount"]
print "Pulled market types page", page, "of", pageCount
#'''
while page < pageCount:
	nextUrl = response["next"]["href"]
	response = requests.get(nextUrl).json()
	marketTypesData.extend(response["items"])
	page += 1
	print "Pulled market types page", page, "of", pageCount
#'''
with open(FILE_MARKETTYPES, 'wt') as outfile:
	pprint.pprint(marketTypesData, stream=outfile)

response = requests.get(CREST_URL_MARKETGROUPS).json()
marketGroupsData = response["items"]

print "Pulled market groups"
with open(FILE_MARKETGROUPS, 'wt') as outfile:
	pprint.pprint(marketGroupsData, stream=outfile)

print "Pulled a total of:"
print "   ", len(marketTypesData), "market types"
print "   ", len(marketGroupsData), "market groups"

# given market types and groups lists, construct market tree
# first create all nodes, then create all parent links (once the parent is guaranteed to exist)
print "Constructing marketTypes and marketGroups maps...", # comma so we don't print a newline
marketTypes = {}
for marketType in marketTypesData:
	node		= MarketNode()
	node.id		= marketType["id"]
	node.name	= marketType["type"]["name"]
	node.crest_url 	= marketType["type"]["href"]
	marketTypes[marketType["id"]] = node
marketGroups = {}
for marketGroup in marketGroupsData:
	node		= MarketNode()
	node.id		= marketGroup["id"]
	node.name	= marketGroup["name"]
	node.crest_url	= marketGroup["href"]
	marketGroups[marketGroup["id"]] = node
for marketType in marketTypesData:
	marketTypes[marketType["id"]].parent = marketGroups[marketType["marketGroup"]["id"]]
for marketGroup in marketGroupsData:
	if "parentGroup" in marketGroup: # not all market groups have parents
		marketGroups[marketGroup["id"]].parent = marketGroups[marketGroup["parentGroup"]["id"]]
print "OK"
print ""

# for each markettype, pull history
# if <2 days history or most recent isn't yesterday, drop market type
# otherwise, for yesterday + today, calculate px*vol and delta

reqsPerSec = round(CREST_RATE_LIMIT * 0.80)
i = 0 # index of next element of marketTypes to process
j = 0 # number of elements processed so far in this bucket (one second)
lock = threading.Lock()
marketTypesToDrop = []

print "Beginning CREST history calls with", NUM_WORKER_THREADS, "threads"
print "Limiting CREST calls to %d/sec" % reqsPerSec
print ""

def resetLimit():
	global i, j
	while True :
		if i == len(marketTypes):
			# if i == 300:
			return
		j = 0
		time.sleep(1)

def worker():
	global i, j
	td = threading.local() # thread-local data
	while True:
		if i == len(marketTypes):
			# if i == 300:
			return
		if j == reqsPerSec:
			time.sleep(0.01)
			continue
		lock.acquire()
		if i == len(marketTypes):
			# if i == 300:
			lock.release()
			return
		if j == reqsPerSec:
			lock.release()
			time.sleep(0.01)
			continue
		# got the lock and we're not up against throttling constraints; proceed
		# print "Processing i =", i
		td.typePair	= marketTypes.items()[i] # locked access of i
		if i % HIST_CALL_PRINT_MOD == 0:
			print "Processing marketType", i, "of", len(marketTypes)
		i += 1
		j += 1
		lock.release()
		td.typeKey 	= td.typePair[0]
		td.typeValue	= td.typePair[1]
		td.url = CREST_URL_PREFIX_HISTORY_FORGE + td.typeValue.crest_url
		td.history = requests.get(td.url).json()

		# if we don't have 2+ dates of market history, drop market type
		if len(td.history["items"]) < 2: # need two, not one, because we calc delta
			# in Python, list.append() is threadsafe; no lock needed
			marketTypesToDrop.append(td.typeKey)
			continue

		# if the most recent market history date isn't targetDate, drop market type
		if td.history["items"][-1]["date"][0:10] != targetDateStr:
			marketTypesToDrop.append(td.typeKey)
			continue

		# if the secondmost recent market history date isn't targetPrevDate, drop market type
		if td.history["items"][-2]["date"][0:10] != targetPrevDateStr:
			marketTypesToDrop.append(td.typeKey)
			continue

		td.typeValue.px_x_vol = td.history["items"][-1]["avgPrice"] * td.history["items"][-1]["volume"]
		td.typeValue.px_x_vol_delta = (td.typeValue.px_x_vol
			- td.history["items"][-2]["avgPrice"] * td.history["items"][-2]["volume"])

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

print "Dropping", len(marketTypesToDrop), "market types with invalid/insufficient market history:"
for marketType in marketTypesToDrop:
	formattedStr = "  %-65s/%8d" % (marketTypes[marketType].name, marketTypes[marketType].id)
	print formattedStr.encode('utf-8')
	#print " ", marketTypes[marketType].name.ljust(65, " "), "/", str(marketTypes[marketType].id).rjust(8, " ")
	marketTypes.pop(marketType, None)
print ""

# given today's mkt vol and daily change, generate Javascript array for Treemap

print "Generating and saving Javascript array for remaining", len(marketTypes), "market types."

js_array_str  = "[\n"
js_array_str += "['Location', 'Parent', 'Market trade volume (size)', 'Market increase/decrease (color)'],\n"
js_array_str += "['Everything', null, 0, 0],\n"

for marketGroup, marketNode in marketGroups.iteritems():
	if marketNode.parent == None:
		js_array_str += "['" + marketNode.name + "', 'Everything', 0, 0],\n"
	else:
		js_array_str += "['" + marketNode.name + "', '" + marketNode.parent.name + "', 0, 0],\n"
for marketType, marketNode in marketTypes.iteritems():
	if marketNode.px_x_vol == None:
		js_array_str += "['" + marketNode.name + "', '" + marketNode.parent.name + "', 0, 0],\n"
	else:
		js_array_str += "['" + marketNode.name + "', '" + marketNode.parent.name + "', " + str(round(marketNode.px_x_vol, 2)) + ", " + str(round(marketNode.px_x_vol_delta, 2)) + "],\n"

js_array_str = js_array_str[:-2] # trim off terminal ",\n"; we want to remove the comma
js_array_str += "\n]"
js_array_str = js_array_str.encode('utf-8')

# save array in two locations: 1) datestamped archive copy 2) running "current" file for display

archiveFileStr = FILE_PREFIX_OUTPUT + targetDateStr
currentFileStr = FILE_PREFIX_OUTPUT + "current"
print "Datestamped JS array output file:   ", archiveFileStr
print "Current JS array output file:       ", currentFileStr
outfile = open(archiveFileStr, "w")
outfile.write(js_array_str)
outfile.close()
shutil.copyfile(archiveFileStr, currentFileStr)
print "Success! Files saved."
