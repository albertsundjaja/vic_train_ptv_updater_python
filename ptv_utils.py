from hashlib import sha1
import hmac
import binascii
import config
import requests
from models.train_route import TrainRoute

URL_ALL_TRAIN_ROUTES = "/v3/routes?route_types=0"

# fill the route_id from ALL_TRAIN_ROUTES
URL_ALL_STATIONS_IN_ROUTES = "/v3/stops/route/{0}/route_type/0"


def _upsert_train_route(route):
    train_route = TrainRoute.objects(route_id=route['route_id'])
    # if not found create new
    if len(train_route) == 0:
        train_route = TrainRoute()
    else:
        train_route = train_route[0]

    train_route.route_id = route['route_id']
    train_route.route_name = route['route_name']
    train_route.save()


def get_encrypted_url(request):
    dev_id = config.DEV_ID
    dev_key = config.DEV_KEY
    # http://timetableapi.ptv.vic.gov.au/v3/routes?
    request = request + ('&' if ('?' in request) else '?')
    # add required devId in the url parameter
    raw = request+'devid={0}'.format(dev_id)
    # calculate the request sha1 hash, it expects bytes key and raw
    hashed = hmac.new(dev_key.encode('utf-8'), raw.encode('utf-8'), sha1)
    signature = hashed.hexdigest()
    return config.PTV_URL+raw+'&signature={0}'.format(signature)


def query_all_train_routes():
    '''
    Query the PTV API for all train routes and updates their info in the db

    this function updates the train_route collection and the run collection
    '''

    query_url = get_encrypted_url(URL_ALL_TRAIN_ROUTES)
    req = requests.get(query_url)
    routes = req.json()['routes']
    #routes = [{'route_service_status': {'description': 'Planned Works', 'timestamp': '2019-12-05T10:34:52.3916923+00:00'}, 'route_type': 0, 'route_id': 99, 'route_name': 'Alamein', 'route_number': '', 'route_gtfs_id': '2-ALM'}, {'route_service_status': {'description': 'Planned Works', 'timestamp': '2019-12-05T10:34:52.3916923+00:00'}, 'route_type': 0, 'route_id': 2, 'route_name': 'Belgrave', 'route_number': '', 'route_gtfs_id': '2-BEL'}]
    for route in routes:
        _upsert_train_route(route)
        

