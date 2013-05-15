import os
import logging

import requests

from itc.core.application import ITCApplication
from itc.parsers.serverparser import ITCServerParser
from itc.conf import *

class ITCServer(object):
    def __init__(self, username, password):
        self._info                  = {'username': username, 'password': password}
        self._loginPageURL          = ITUNESCONNECT_MAIN_PAGE_URL
        self._parser                = ITCServerParser()
        self.applications           = {}
        self.isLoggedIn             = self.__checkLogin()


    def __cleanup(self):
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
        

    def __checkLogin(self, mainPageTree=None):
        if mainPageTree == None:
            mainPageTree = self._parser.parseTreeForURL(self._loginPageURL)

        if (mainPageTree == None) or (not self._parser.isLoggedIn(mainPageTree)):
            logging.debug('Check login: not logged in!')
            self.__cleanup()
            return False

        logging.debug('Check login: logged in!')
        return True


    def logout(self):
        if not self.isLoggedIn or not self._logoutURL:
            return

        requests.get(ITUNESCONNECT_URL + self._logoutURL, cookies=cookie_jar)
        self.__cleanup()


    def login(self, login=None, password=None):
        if self.isLoggedIn:
            logging.debug('Login: already logged in')
            return

        tree = self._parser.parseTreeForURL(self._loginPageURL)
        forms = tree.xpath("//form")

        if len(forms) == 0:
            raise
        
        form = forms[0]
        actionURL = form.attrib['action']
        payload = {'theAccountName': (self._info['username'] if login == None else login)
                 , 'theAccountPW': self._info['password'] if password == None else password}
        mainPageTree = self._parser.parseTreeForURL(actionURL, method="POST", payload=payload)

        self.isLoggedIn = self.__checkLogin(mainPageTree=mainPageTree);
        if self.isLoggedIn:
            logging.info("Login: logged in. Session cookies are saved to " + cookie_file)
            logging.debug(cookie_jar)
            cookie_jar.save(cookie_file, ignore_discard=True)
        else:
            raise Exception('Cannot continue: login failed. Please check username/password')


    def fetchApplicationsList(self):
        if not self.isLoggedIn:
            raise Exception('Get applications list: not logged in')

        applicationsData = self._parser.getApplicationsData()
        for applicationData in applicationsData:
            name = applicationData.name
            link = applicationData.link
            applicationId = applicationData.applicationId

            application = ITCApplication(name=name, applicationId=applicationId, link=link)
            self.applications[applicationId] = application

    def createNewApp(self, appDictionary=None):
        if appDictionary == None or len(appDictionary) == 0 or 'new app' not in appDictionary: # no data to create app from
            return

        metadata = self._parser.parseFirstAppCreatePageForm()
        print metadata
        

