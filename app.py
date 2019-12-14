import config
import mongo
import ptv_utils
import sys
import schedule
import time

# update the dev id and dev key
config.DEV_ID = sys.argv[1]
config.DEV_KEY = sys.argv[2]

def init():
    """
    Initialize and populate our db with data

    """
    ptv_utils.query_and_update_all_train_routes()
    ptv_utils.query_and_update_all_train_stops()
    ptv_utils.query_and_update_all_train_runs()
    ptv_utils.query_and_update_train_direction()
    ptv_utils.query_and_update_train_route_stops_order()


def update():
    """
    Update db periodically
    """
    ptv_utils.query_and_update_all_train_runs()


init()
schedule.every().day.at("22:00").do(update)

while True:
    schedule.run_pending()
    time.sleep(10)