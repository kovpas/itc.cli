import json
import logging

statuses_map = {}

class APP_STATUS:
    PREPARE_FOR_UPLOAD = 0
    WAITING_FOR_UPLOAD = 1
    UPLOAD_RECEIVED = 2
    WAITING_FOR_REVIEW = 3
    IN_REVIEW = 4
    PENDING_CONTRACT = 5
    WAITING_FOR_EXPORT_COMPLIANCE = 6
    PENDING_DEVELOPER_RELEASE = 7
    PROCESSING_FOR_APP_STORE = 8
    PENDING_APPLE_RELEASE = 9
    READY_FOR_SALE = 10
    REJECTED = 11
    METADATA_REJECTED = 12
    REMOVED_FROM_SALE = 13
    DEVELOPER_REJECTED = 14
    DEVELOPER_REMOVED_FROM_SALE = 15
    INVALID_BINARY = 16
    MISSING_SCREENSHOT = 17

__CAN_BE_REJECTED = [APP_STATUS.MISSING_SCREENSHOT, APP_STATUS.WAITING_FOR_EXPORT_COMPLIANCE\
                    , APP_STATUS.WAITING_FOR_REVIEW \
                    #, APP_STATUS.IN_REVIEW
                    , APP_STATUS.PENDING_DEVELOPER_RELEASE, APP_STATUS.PENDING_APPLE_RELEASE]

def __parse_statuses_map():
    try:
        try:
             import pkgutil
             data = pkgutil.get_data(__name__, 'statuses.json')
        except ImportError:
             import pkg_resources
             data = pkg_resources.resource_string(__name__, 'statuses.json')
        globals()['statuses_map'] = json.loads(data)
    except BaseException:
        raise 

def __statuses():
    if globals()['statuses_map'] == None or len(globals()['statuses_map']) == 0:
        __parse_statuses_map()
        logging.debug(globals()['statuses_map'])

    return globals()['statuses_map']

def statusByStatusString(statusString):
    return __statuses().get(statusString)

def canBeRejected(status):
    return status['id'] in __CAN_BE_REJECTED
