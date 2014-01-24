import json
import logging

statuses_map = {}

class APP_STATUS:
    PREPARE_FOR_UPLOAD = 1
    WAITING_FOR_UPLOAD = 2
    UPLOAD_RECEIVED = 3
    WAITING_FOR_REVIEW = 4
    IN_REVIEW = 5
    PENDING_CONTRACT = 6
    WAITING_FOR_EXPORT_COMPLIANCE = 7
    PENDING_DEVELOPER_RELEASE = 8
    PROCESSING_FOR_APP_STORE = 9
    PENDING_APPLE_RELEASE = 10
    READY_FOR_SALE = 11
    REJECTED = 12
    METADATA_REJECTED = 13
    REMOVED_FROM_SALE = 14
    DEVELOPER_REJECTED = 15
    DEVELOPER_REMOVED_FROM_SALE = 16
    INVALID_BINARY = 17
    MISSING_SCREENSHOT = 18

    __CAN_BE_REJECTED = [MISSING_SCREENSHOT, WAITING_FOR_EXPORT_COMPLIANCE, WAITING_FOR_REVIEW \
                        #, IN_REVIEW
                        , PENDING_DEVELOPER_RELEASE, PENDING_APPLE_RELEASE]
    def can_be_rejected(status):
        return status['id'] in __CAN_BE_REJECTED

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
