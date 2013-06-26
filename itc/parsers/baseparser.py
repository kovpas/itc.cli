import logging

import requests
from bs4 import BeautifulSoup

from itc.parsers import htmlParser
from itc.conf import *

class BaseParser(object):
    parser = None
    requests_session = None
    def __init__(self):
        self.requests_session = requests.session()
        self.parser = htmlParser

    def parseTreeForURL(self, url, method="GET", payload=None, debugPrint=False):
        response = None
        if method == "GET":
            response = self.requests_session.get(ITUNESCONNECT_URL + url, cookies=cookie_jar)
        elif method == "POST":
            response = self.requests_session.post(ITUNESCONNECT_URL + url, payload, cookies=cookie_jar)

        if response == None:
            raise

        if debugPrint or config.options['--verbose'] == 2:
            if config.options['-f']:
                logging.debug(BeautifulSoup(response.content).prettify())
            elif debugPrint:
                logging.info(BeautifulSoup(response.content).prettify())
            else:
                logging.debug(response.content)

        if response.status_code != 200:
            logging.error('Wrong response from itunesconnect. Status code: ' + str(response.status_code) + '. Content:\n' + response.text)
            return None

        return self.parser.parse(response.text)