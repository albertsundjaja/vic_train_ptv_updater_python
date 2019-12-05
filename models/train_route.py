from mongoengine import *

class TrainRoute(Document):
    route_id = IntField(unique=True)
    route_name = StringField()
    stops_order = ListField(DictField)

