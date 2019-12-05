import pymongo
from mongoengine import connect

'''
_client = pymongo.MongoClient("localhost", 27017, maxPoolSize=100)
_document = _client['vic_train_board']

def getTrainRoutesCol():
    return _document['routes']
'''

connect('vic_train_board')


