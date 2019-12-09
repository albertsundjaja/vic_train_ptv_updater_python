from hashlib import sha1
import hmac
import binascii
import config
import requests
from models.train_route import TrainRoute
from models.run import Run, StopInRun
from models.train_stop import TrainStop
from models.train_direction import TrainDirection
import time
from datetime import datetime
import dateutil.parser

URL_ALL_TRAIN_ROUTES = "/v3/routes?route_types=0"

# fill the route_id from ALL_TRAIN_ROUTES
URL_ALL_STATIONS_IN_ROUTES = "/v3/stops/route/{0}/route_type/0"

# fill the stop id
URL_ALL_RUNS_FROM_STOP = "/v3/departures/route_type/0/stop/{0}"

# fill the direction_id and route type
URL_DIRECTION_FROM_DIRECTION_ID = "/v3/directions/{0}/route_type/{1}"

URL_ALL_LINES_ID = "/v2/lines/mode/0"


def _upsert_train_route(route):
    '''
    this function will try to find existing route,
    if exists do an update instead of insert
    '''
    train_route = TrainRoute.objects(route_id=route['route_id'])
    # if not found create new
    if len(train_route) == 0:
        train_route = TrainRoute()
    else:
        train_route = train_route[0]

    train_route.route_id = route['route_id']
    train_route.route_name = route['route_name']
    train_route.save()


def _upsert_stop(stop):
    """
    this function will try to find existing stop,
    if exists do an update instead of insert
    """

    train_stop = TrainStop.objects(stop_id=stop['stop_id'])
    # if not found create new
    if len(train_stop) == 0:
        train_stop = TrainStop()
    else:
        train_stop = train_stop[0]

    train_stop.stop_id = stop['stop_id']
    train_stop.stop_name = stop['stop_name']
    train_stop.stop_subur = stop['stop_suburb']
    train_stop.stop_latitude = stop['stop_latitude']
    train_stop.stop_longitude = stop['stop_longitude']
    train_stop.save()


def _upsert_run(departure, route_type):
    '''
    this function will try to find existing run,
    if exists do an update instead of insert

    Args:
        route (dict): the departure dict
        route_type (int): the type of the route e.g. 0 = train
    '''
    train_run = Run.objects(run_id=departure['run_id'])
    if len(train_run) == 0:
        train_run = Run()
    else:
        train_run = train_run[0]

    train_run.run_id = departure['run_id']
    train_run.route_type = route_type

    # get all the stop ids that is already in the train run for checking
    stop_in_train_run_ids = [stop.stop_id for stop in train_run.stops]

    if departure['stop_id'] not in stop_in_train_run_ids:
        stop_in_run = StopInRun()
        stop_in_run.stop_id = departure['stop_id']
        train_stop = TrainStop.objects(stop_id=departure['stop_id'])
        stop_in_run.stop_name = train_stop[0].stop_name

        stop_in_run.route_id = departure['route_id']
        stop_in_run.direction_id = departure['direction_id']
        # the departure date is in ISO8601 RFC3339 format
        parsed_date = dateutil.parser.parse(departure['scheduled_departure_utc'])
        stop_in_run.scheduled_depatures = parsed_date
        stop_in_run.platform_number = departure['platform_number']
        stop_in_run.disruption_ids = departure['disruption_ids']
        train_run.stops.append(stop_in_run)

    train_run.save()


def _upsert_direction(direction):
    train_direction = TrainDirection.objects(direction_id = direction['direction_id'])
    if len(train_direction) == 0:
        train_direction = TrainDirection()
        train_direction.direction_id = direction['direction_id']

    else:
        train_direction = train_direction[0]

    train_direction.direction_name = direction['direction_name']
    train_direction.route_id = direction['route_id']
    train_direction.route_type = direction['route_type']
    train_direction.route_direction_description = direction['route_direction_description']
    train_direction.save()


def get_encrypted_url(request):
    """
    PTV requires that every URL has encrypted signature of its parameters and route

    Args:
        request (string): the desired path that we want to access e.g. /v3/routes
    
    Returns:
        string: full url with encryption
    """

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


def query_and_update_all_train_routes():
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


def query_and_update_all_train_stops():
    """
    Query the PTV API for all train stops

    It will loop through all train routes and get the station that it stops

    this function update the train_stop collection
    """

    routes = TrainRoute.objects()
    for route in routes:
        query_url = get_encrypted_url(URL_ALL_STATIONS_IN_ROUTES.format(route.route_id))
        req = requests.get(query_url)
        stops = req.json()['stops']
        for stop in stops:
            _upsert_stop(stop)
            time.sleep(0.5)


def query_and_update_all_train_runs(counts=300):
    """
    Query the PTV api for all train runs

    It will loop through all train stops and get the runs for that station

    Args:
        count (int): get the runs schedule for these number of counts

    will update run collection

    """
    stops = TrainStop.objects()
    now = datetime.now()
    startDate = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat() + 'Z'

    #i = 0
    for stop in stops:
        #i += 1
        #print("processing stops {0}/{1}".format(i, len(stops)))
        url = URL_ALL_RUNS_FROM_STOP.format(stop.stop_id) + "?date_utc={0}&max_results={1}".format(startDate, counts)
        query_url = get_encrypted_url(url)
        req = requests.get(query_url)
        runs = req.json()['departures']
        for run in runs:
            _upsert_run(run, 0)
        time.sleep(0.5) 


def query_and_update_train_direction_id():
    """
    Query PTV api for all direction id

    Loop through all DISTINCT direction_id from runs

    will update train_direction collection
    """
    distinct_direction_id = Run.objects().distinct(field="stops.direction_id")
    
    for direction_id in distinct_direction_id:
        url = get_encrypted_url(URL_DIRECTION_FROM_DIRECTION_ID.format(direction_id, 0))
        req = requests.get(url)
        directions = req.json()['directions']
        for direction in directions:
            _upsert_direction(direction)


def deduce_train_route_stops_order():
    """
    This will make use of run collection to deduce the stop order for a given route

    """

    routes = TrainRoute.objects()
    for route in routes:
        print(route.route_id)
        route.stops_order = []
        runs = Run.objects(stops__route_id=route['route_id'])
        longest_stops = []
        for run in runs:
            if len(run.stops) > len(longest_stops):
                longest_stops = run.stops

        longest_stops = sorted(longest_stops, key=lambda stop: stop.scheduled_depatures)
        for stop in longest_stops:
            stop_dict = {
                "stop_id": stop.stop_id,
                "stop_name": stop.stop_name,
                "stop_suburb": stop.stop_suburb
            }
            route.stops_order.append(stop_dict)
        
        route.save()
        break

    
def _rename_field_in_EmbbededDocumentListField():
    """
    used to rename field inside list of embbedded document
    """

    runs = Run.objects()
    for run in runs:
        stops = run.stops
        for stop in stops:
            stop.scheduled_departures = stop.scheduled_depatures
        
        run.stops=stops
        
        run.save()

