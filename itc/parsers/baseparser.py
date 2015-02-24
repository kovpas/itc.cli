import logging

import requests
from bs4 import BeautifulSoup
import json

from itc.parsers import htmlParser
from itc.conf import *

__cookies__ = None

class BaseParser(object):
    parser = None
    requests_session = None
    def __init__(self):
        self.requests_session = requests.session()
        self.parser = htmlParser

    def parseTreeForURL(self, url, method="GET", payload=None, debugPrint=False, isJSON=False):
        response = None
        if method == "GET":
            response = self.requests_session.get(ITUNESCONNECT_URL + url, cookies=globals()['__cookies__'])
        elif method == "POST":
            response = self.requests_session.post(ITUNESCONNECT_URL + url, payload, cookies=globals()['__cookies__'])

        if response == None:
            raise

        if not globals()['__cookies__']:
            globals()['__cookies__'] = response.cookies

        print globals()['__cookies__']

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

        if not isJSON:
            return self.parser.parse(response.text)

        return json.loads(response.text)