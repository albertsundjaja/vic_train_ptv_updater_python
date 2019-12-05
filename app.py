from hashlib import sha1
import hmac
import binascii
import config
import mongo
import ptv_utils
import sys

# update the dev id and dev key
config.DEV_ID = sys.argv[1]
config.DEV_KEY = sys.argv[2]

#print(getUrl('/v3/routes?route_types=0'))
#results = mongo.test_col.find({"no":1})
#print(results[:])

ptv_utils.query_all_train_routes()
