from mongoengine import *

class TrainDirection(Document):
    direction_id = IntField(unique=True)
    direction_name = StringField()
    route_id = IntField()
    route_type = IntField()
    route_direction_description = StringField()