import os
import logging
from datetime import datetime

import requests

from itc.core.application import ITCApplication
from itc.parsers.serverparser import ITCServerParser
from itc.core.baseobject import ITCImageUploader
from itc.util import languages
from itc.conf import *

class ITCServer(ITCImageUploader):
    def __init__(self, username, password):
        super(ITCServer, self).__init__()

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

        newAppMetadata = appDictionary['new app']
        metadata = self._parser.parseFirstAppCreatePageForm()
        formData = {}
        formNames = metadata.formNames
        submitAction = metadata.submitAction
        
        formData[formNames['default language']] = metadata.languageIds[languages.languageNameForId(newAppMetadata['default language'])]
        formData[formNames['app name']]         = newAppMetadata['name']
        formData[formNames['sku number']]       = newAppMetadata['sku number']
        formData[formNames['bundle id suffix']] = newAppMetadata['bundle id suffix']
        formData[formNames['bundle id']]        = next(value for (key, value) in metadata.bundleIds.iteritems() if key.endswith(' - ' + newAppMetadata['bundle id']))
        
        formData[formNames['continue action'] + '.x'] = "0"
        formData[formNames['continue action'] + '.y'] = "0"

        logging.debug(formData)
        postFormResponse = requests.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        metadata = self._parser.parseSecondAppCreatePageForm(postFormResponse.text)
        formData = {}
        formNames = metadata.formNames
        submitAction = metadata.submitAction
        date = datetime.strptime(newAppMetadata['availability date'], '%b %d %Y')

        formData[formNames['date day']]   = date.day - 1
        formData[formNames['date month']] = date.month - 1
        formData[formNames['date year']]  = date.year - datetime.today().year
        formData[formNames['price tier']] = newAppMetadata['price tier']
        if 'discount' in newAppMetadata and newAppMetadata['discount']:
            formData[formNames['discount']] = formNames['discount']

        include = 'countries' in newAppMetadata \
            and isinstance(newAppMetadata['countries'], dict) \
            and 'type' in newAppMetadata['countries'] and newAppMetadata['countries']['type'] == 'include' \
            and 'list' in newAppMetadata['countries']
        exclude = 'countries' in newAppMetadata \
            and isinstance(newAppMetadata['countries'], dict) \
            and 'type' in newAppMetadata['countries'] and newAppMetadata['countries']['type'] == 'exclude' \
            and 'list' in newAppMetadata['countries']

        if include:
            for country in newAppMetadata['countries']['list']:
                logging.debug("Including " + country)
                formData[metadata.countries[country]] = metadata.countries[country]
        else:
            for country, val in metadata.countries.items():
                if not exclude or country not in newAppMetadata['countries']['list']:
                    formData[val] = val
                else:
                    logging.debug("Excluding " + country)


        formData[formNames['continue action'] + '.x'] = "0"
        formData[formNames['continue action'] + '.y'] = "0"

        postFormResponse = requests.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        logging.debug(postFormResponse.text)
