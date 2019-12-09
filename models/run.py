from mongoengine import *

class StopInRun(EmbeddedDocument):
    stop_id = IntField()
    stop_name = StringField()
    route_id = IntField()
    direction_id = IntField()
    scheduled_depatures = DateTimeField()
    scheduled_departures = DateTimeField()
    platform_number = StringField()
    disruption_ids = ListField(IntField())

class Run(Document):
    run_id = IntField(unique=True)
    route_type = IntField()
    stops = EmbeddedDocumentListField(StopInRun)