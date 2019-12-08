from mongoengine import *

class TrainStop(Document):
    stop_id = IntField
    stop_name = StringField
    stop_suburb = StringField
    stop_latitude = FloatField
    stop_longitude = FloatField