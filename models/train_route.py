from mongoengine import *
from models.train_stop import TrainStop

class TrainRoute(Document):
    route_id = IntField(unique=True)
    route_name = StringField()

