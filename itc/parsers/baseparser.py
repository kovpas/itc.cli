import logging

import requests

from itc.parsers import htmlParser
from itc.conf import *

class BaseParser(object):
    parser = None
    def __init__(self):
        self.parser = htmlParser

    def parseTreeForURL(self, url, method="GET", payload=None, debugPrint=False):
        response = None
        if method == "GET":
            response = requests.get(ITUNESCONNECT_URL + url, cookies=cookie_jar)
        elif method == "POST":
            response = requests.post(ITUNESCONNECT_URL + url, payload, cookies=cookie_jar)

        if response == None:
            raise

        if debugPrint:
            logging.debug(response.content)

        if response.status_code != 200:
            logging.error('Wrong response from itunesconnect. Status code: ' + str(response.status_code) + '. Content:\n' + response.text)
            return None

        return self.parser.parse(response.text)