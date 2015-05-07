mongodb-pubnub
==============

Neo4j Integration with PubNub Data Stream

#INTRODUCTION
This application demonstrates the use of Neo4j database with PubNub data stream. With the help of PubNub data stream SDKs we can stream the data fetched from Neo4j to remote users.

This application builds a simple stockticker for fetching and dislaying major stock indices from the world. The application has two components.The server simulates a stock market feed and implements the PubNub broadcast server. The client runs as a front end web application for displaying the price counters.

#PRECONDITION

1. You will need python2 installed on the server computer with pymongo and PubNub's Python SDK installed. Refer to the official docs of PyMongo and PubNub SDKs for installation instructions
2. You will need a PubNub sandbox account to publish and subscribe your data. You need to add your publish and subscribe key on the server and client program. Search for the string "YOUR PUBNUB KEYS" in the code to locate the line where you need to add the keys". For more details refer the PubNub SDK documention for Python and Javascript.


#SETUP

##Server Setup
Open a console or terminal on the server and run the server program as follows ( Assuming that you are in the server directory)
> python stocktickerneo.py 80 8080



