import sys

import threading
from Queue import Queue

import time
import datetime
import random
import json
import py2neo
from py2neo import Graph, Path

NEO_PROTOCOL = 'http'
NEO_HOST = 'localhost'
NEO_PORT = 7474
NEO_USER = 'neo4j'
NEO_PASSWORD = 'password'


from Pubnub import Pubnub

'''
Global Data - Queue
'''
globalQueueRef = None


'''
Client Listener Thread
'''
class ClientListenerThread(threading.Thread):

	def __init__(self,server,port,queueRef,pnb):
		threading.Thread.__init__(self)
		graph = Graph('%s://%s:%s@%s:%s/db/data/' % 
		(NEO_PROTOCOL, NEO_USER, NEO_PASSWORD, NEO_HOST, NEO_PORT))

		self.clientQueue = queueRef 
		self.pnb = pnb

	def run(self):
		
		try :
			while True :
				print "Before queue block"
				data = self.clientQueue.get()
				print "After queue block"
				print data

				req = json.loads(data)
				

#				self.publishPriceHistory(req['name'],req['backtime'],req['channel'])

		except Exception as e:
			print "Failure in Client Request Handling"
			print e

	def publishPriceHistory(self,idxname,time,channel):

		broadcastDict = []

		timefrom = self.getLastUpdateTime(idxname)

		timefrom = timefrom - (time * 60)

		it = self.coll.find({'name': idxname , 'time' : { '$gte' : timefrom } })

		for item in it:

			broadcastDict.append({ "name"   : item['name'],
						      "value"  : item['value'],
						      "change" : item['change'],
						      "time"   : item['time']
						})

		broadcastData = json.dumps(broadcastDict)
		print 'Broadcasting Price History : ' + broadcastData
		self.pnb.publish(channel,broadcastData)


	def getLastUpdateTime(self,idxname):
		
		query = [{'$group': {'_id': '$name', 'maxValue': {'$max': '$time'}}}]

		result = self.coll.aggregate(query)

		for entry in result['result']:
			if (entry['_id'] == idxname):
				return entry['maxValue'] 
			
		return None

'''
Description - Main server loop

Data will be stored in the following JSON format

	{
		"name"   : "NASDAQ"  ,
		"value"  : "6345.25" ,
		"change" : "+13.45"  ,
		"time"   : 1412322567
	}

'''
def startStockPicker(server,port):

	global globalQueueRef
	global graph

	#Step 1 - Initialize MongoDB & PubNub Connection
	# py2neo.set_auth_token('%s:%s' % (NEO_HOST, NEO_PORT), NEO_AUTH_TOKEN)
	graph = Graph('%s://%s:%s@%s:%s/db/data/' % 
	(NEO_PROTOCOL, NEO_USER, NEO_PASSWORD, NEO_HOST, NEO_PORT))

	#YOUR PUBNUB KEYS - Replace the publish_key and subscriber_key below with your own keys
	pubnub = Pubnub(publish_key="<your pub key>",subscribe_key="<your sub key>")

	#Step 2 - Check and define the metadata ( index names )
	metaDataInit()

	#Step 3 - Set the parameters , max periodicity , random range
	updateTime = 10 #Max ten seconds for every price update
	numOfItems = 4  #Four indices to manage

	random.seed()

	#Step 4 - Setup the Queue and ClientListener Thread
	clientQueue = Queue()
	clientListener = ClientListenerThread(server,port,clientQueue,pubnub)
	clientListener.start()

	globalQueueRef = clientQueue

	#Step 5 - Setup PubNub Subscription for client requests
	pubnub.subscribe("stockhistory", historyCallback,historyError)

	#Step 6 - Start the stock picking loop
	while True:

		#Step 6.1 - Wait for random time
		time.sleep(random.randint(1,updateTime))
		
		#Step 6.2 - Wake up and update the stock price for one of the index
		newPriceData = getUpdatedPrice()

		#Step 6.3 - Update the new price in DB
		print "New Price Update " + str(newPriceData)

		#Step 6.4 - Publish over Pubnub , stockdata channel
		broadcastData = { 'name'   : newPriceData['name'],
						  'value'  : newPriceData['value'],
						  'change' : newPriceData['change'],
						  'time' : newPriceData['time'],

						}

		pubnub.publish('stockdata',json.dumps(broadcastData))

		
		



'''
Description - Populate the index names to track and initial database
'''
def metaDataInit():
	global metadataDescr

	#Four major world indices to manage
	metadataDescr = ['NASDAQ','DOWJONES','FTSE','NIKKEI']
	
	cyres = graph.cypher.execute("""MERGE (s:Stock {name:'FTSE', value:6637.92, change:-16.02 , time : 1})""");
	cyres = graph.cypher.execute("""MERGE (s:Stock {name:'NASDAQ', value:4630.60, change:+6.06 , time : 1})""");
	cyres = graph.cypher.execute("""MERGE (s:Stock {name:'DOWJONES', value:17630.60, change:-36.02 , time : 1})""");
	cyres = graph.cypher.execute("""MERGE (s:Stock {name:'NIKKEI', value:17336.12, change:-23.02 , time : 1})""");
		


'''
Description - This function simulates the stock index price update
			  Gets the new price details for indices based on random
			  selection

Return      - Returns the JSON formatted index name, price , delta and time
'''
def getUpdatedPrice():
	
	#Random select the index whose price is to be updated
	idx = random.sample(metadataDescr,1)

	#Randomly get a price increment in range of 1.0 to 10.0
	#It is assumed that price delta will always be in this range
	pricedelta = round(random.uniform(1.0,10.0),2)

	#Randomly get the direction of price change
	#Either positive or negative
	pricedir = random.randint(0,1)

	#Get the current price of index
	#currprice = getCurrentPrice(coll,idx[0])
	queryString = """MATCH (s:Stock {name:'"""
	queryString = queryString + idx[0]
	queryString = queryString + """'}) return s.value""" 
	print queryString
	cyres = graph.cypher.execute(queryString);
	print cyres
	for r in cyres:
		currprice = r[0]

	#Calculate new price of index based on pricedelta and pricedir
	if(pricedir):
		newprice = round(currprice + pricedelta,2)
		pricedeltastr = '+'+str(pricedelta)
	else :
		newprice = round(currprice - pricedelta,2)
		pricedeltastr = '-'+str(pricedelta)
		
	queryString = """MATCH (s:Stock {name:'"""
	queryString = queryString + idx[0]
	queryString = queryString + """'}) SET s.value = """ + str(newprice)
	print queryString 
	cyres = graph.cypher.execute(queryString);
		

	print "New Price for " + " : " + str(newprice)
	#Get the current time of update
	updateTime = getCurrentTimeInSecs()

	#Return the new index price
	return {
			'name'     : idx[0] ,
			'value'    : newprice ,
			'change'   : pricedeltastr ,
			'time'     : updateTime     
		}

'''
Description - This function fetches the most recent price update of 
              an index idxname 

Returns -  Last updated price
'''
def getCurrentPrice(coll,idxname):
	
	query = [{'$group': {'_id': '$name', 'maxValue': {'$max': '$time'}}}]

	result = coll.aggregate(query)

	for entry in result['result']:
		if (entry['_id'] == idxname):
			it = coll.find({'name' : idxname , 'time' : entry['maxValue'] }).limit(1)
			val =  it.next()['value']
			print "Last Updated Price for " + idxname + " : " + str(val)
			return val
	return None

	'''
	Description - This function simulates the stock index price update
			  Gets the new price details for indices based on random
			  selection

	Return      - Returns the JSON formatted index name, price , delta and time
	'''
	def getUpdatedPrice(coll):

		#Random select the index whose price is to be updated
		idx = random.sample(metadataDescr,1)

		#Randomly get a price increment in range of 1.0 to 10.0
		#It is assumed that price delta will always be in this range
		pricedelta = round(random.uniform(1.0,10.0),2)

		#Randomly get the direction of price change
		#Either positive or negative
		pricedir = random.randint(0,1)

		#Get the current price of index
		currprice = getCurrentPrice(coll,idx[0])

		#Calculate new price of index based on pricedelta and pricedir
		if(pricedir):
			newprice = round(currprice + pricedelta,2)
			pricedeltastr = '+'+str(pricedelta)
		else :
			newprice = round(currprice - pricedelta,2)
			pricedeltastr = '-'+str(pricedelta)

		print "New Price for " + idx[0] + " : " + str(newprice)
		#Get the current time of update
		updateTime = getCurrentTimeInSecs()

		#Return the new index price
		return {
				'name'     : idx[0] ,
				'value'    : newprice ,
				'change'   : pricedeltastr ,
				'time'     : updateTime     
			}

'''
Description - Get the current system time in unix timestamp format
'''
def getCurrentTimeInSecs():
	
	dtime = datetime.datetime.now()

	ans_time = time.mktime(dtime.timetuple())	

	return int(ans_time)

'''
PubNub Callback for inciming requests on global listening channel
'''
def historyCallback(message, channel):
	global globalQueueRef

	print "Received Historical Data Request :" + message
	globalQueueRef.put(message) # Read end in the CLientListenerThread


def historyError(message):

	print "Error in receiving Historical Data Request : " + message

if __name__ == '__main__':

	print sys.argv
	if (len(sys.argv) == 3):
		
		startStockPicker(sys.argv[1],int(sys.argv[2]))
	else:
		print "Error in arguments"
