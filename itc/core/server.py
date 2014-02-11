import os
import logging
from datetime import datetime

import requests

from itc.core.application import ITCApplication
from itc.parsers.serverparser import ITCServerParser
from itc.core.imageuploader import ITCImageUploader
from itc.util import languages
from itc.util import dataFromStringOrFile
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

        if (mainPageTree == None) or (not self._parser.isLoggedIn(self.checkContinueButton(mainPageTree))):
            logging.debug('Check login: not logged in!')
            self.__cleanup()
            return False

        logging.debug('Check login: logged in!')
        return True


    def logout(self):
        if not self.isLoggedIn or not self._logoutURL:
            return

        self._parser.requests_session.get(ITUNESCONNECT_URL + self._logoutURL, cookies=cookie_jar)
        self.__cleanup()

    def checkContinueButton(self, mainPageTree):
        continueHref = self._parser.loginContinueButton(mainPageTree)
        if continueHref != None and config.options['-z']:
            mainPageTree = self._parser.parseTreeForURL(continueHref)
            self.isLoggedIn = self.__checkLogin(mainPageTree=mainPageTree);
        elif continueHref != None:
            raise Exception('Cannot continue: There\'s a form after login, which needs your attention.\n\t\tPlease, use -z command line option in order to suppress this check and automatically continue.')

        return mainPageTree

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
                 , 'theAccountPW': (self._info['password'] if password == None else password)
                 , '1.Continue.x': 60
                 , '1.Continue.y': 27
                 , 'theAuxValue': ''}

        mainPageTree = self._parser.parseTreeForURL(actionURL, method="POST", payload=payload)

        self.isLoggedIn = self.__checkLogin(mainPageTree=mainPageTree);
        if not self.isLoggedIn:
            mainPageTree = self.checkContinueButton(mainPageTree)

        if self.isLoggedIn:
            logging.info("Login: logged in. Session cookies are saved to " + cookie_file)
            # logging.debug(cookie_jar)
            cookie_jar.save(cookie_file, ignore_discard=True)
        else:
            raise Exception('Cannot continue: login failed. Please check username/password')

    def getApplicationById(self, applicationId):
        if not self.isLoggedIn:
            raise Exception('Get applications list: not logged in')
        
        applicationData = self._parser.getApplicationDataById(applicationId)
        application = None
        if (applicationData != None):
            name = applicationData.name
            link = applicationData.link
            applicationId = applicationData.applicationId

            application = ITCApplication(name=name, applicationId=applicationId, link=link)
        
        return application

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

    def __manageCountries(self, serverCountries, countries, formData):
        include = countries \
            and isinstance(countries, dict) \
            and 'type' in countries and countries['type'] == 'include' \
            and 'list' in countries
        exclude = countries \
            and isinstance(countries, dict) \
            and 'type' in countries and countries['type'] == 'exclude' \
            and 'list' in countries

        if include:
            for country in countries['list']:
                logging.debug("Including " + country)
                formData[serverCountries[country]] = serverCountries[country]
        else:
            for country, val in serverCountries.items():
                if not exclude or country not in countries['list']:
                    formData[val] = val
                else:
                    logging.debug("Excluding " + country)


    def createNewApp(self, appDictionary=None, filename_format=None):
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
        secondPageTree = self._parser.parseTreeForURL(submitAction, method="POST", payload=formData)
        errors = self._parser.checkPageForErrors(secondPageTree)

        if errors != None and len(errors) != 0:
            for error in errors:
                logging.error(error)

            return

        metadata = self._parser.parseSecondAppCreatePageForm(secondPageTree)
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

        if 'countries' in newAppMetadata:
            self.__manageCountries(metadata.countries, newAppMetadata['countries'], formData)

        formData[formNames['continue action'] + '.x'] = "0"
        formData[formNames['continue action'] + '.y'] = "0"

        thirdPageTree = self._parser.parseTreeForURL(submitAction, method="POST", payload=formData)
        errors = self._parser.checkPageForErrors(thirdPageTree)

        if errors != None and len(errors) != 0:
            for error in errors:
                logging.error(error)

            return

        metadata = self._parser.parseThirdAppCreatePageForm(thirdPageTree, fetchSubcategories=newAppMetadata['primary category'])
        
        formData = {}
        formNames = metadata.formNames

        iconUploadScreenshotForm    = formNames['iconUploadScreenshotForm'] 
        iphoneUploadScreenshotForm  = formNames['iphoneUploadScreenshotForm'] 
        iphone5UploadScreenshotForm = formNames['iphone5UploadScreenshotForm']
        ipadUploadScreenshotForm    = formNames['ipadUploadScreenshotForm']
        tfUploadForm                = formNames['tfUploadForm']

        iconUploadScreenshotJS    = iconUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        iphoneUploadScreenshotJS  = iphoneUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        iphone5UploadScreenshotJS = iphone5UploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        ipadUploadScreenshotJS    = ipadUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        tfUploadJS                = tfUploadForm.xpath('../following-sibling::script/text()')[0]

        self._uploadSessionData['icon'] = dict({'action': iconUploadScreenshotForm.attrib['action']
                                                        , 'key': iconUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                      }, **self.parseStatusURLSFromScript(iconUploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPhone] = dict({'action': iphoneUploadScreenshotForm.attrib['action']
                                                        , 'key': iphoneUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                      }, **self.parseURLSFromScript(iphoneUploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPhone5] = dict({'action': iphone5UploadScreenshotForm.attrib['action']
                                                         , 'key': iphone5UploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                       }, **self.parseURLSFromScript(iphone5UploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPad] = dict({'action': ipadUploadScreenshotForm.attrib['action']
                                                      , 'key': ipadUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                    }, **self.parseURLSFromScript(ipadUploadScreenshotJS))
        self._uploadSessionData['tf'] = dict({'action': tfUploadForm.attrib['action']
                                                      , 'key': tfUploadForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                    }, **self.parseStatusURLSFromScript(tfUploadJS))

        self._uploadSessionId = iphoneUploadScreenshotForm.xpath('.//input[@name="uploadSessionID"]/@value')[0]

        for device_type in ['icon', DEVICE_TYPE.iPhone, DEVICE_TYPE.iPhone5, DEVICE_TYPE.iPad]:
            self._images[device_type] = self.imagesForDevice(device_type)

        logging.debug(self._images)

        #uploading icon
        self.uploadScreenshot('icon', newAppMetadata['large app icon']['file name format'])
        self._images['icon'] = self.imagesForDevice('icon')

        screenshots = newAppMetadata['screenshots']
        replace_language = ALIASES.language_aliases.get(newAppMetadata['default language'], newAppMetadata['default language'])
        langImagePath = filename_format.replace('{language}', replace_language)

        for dType, indexes in screenshots.items():
            device_type = None
            if dType.lower() == 'iphone':
                device_type = DEVICE_TYPE.iPhone
            elif dType.lower() == 'iphone 5':
                device_type = DEVICE_TYPE.iPhone5
            elif dType.lower() == 'ipad':
                device_type = DEVICE_TYPE.iPad

            replace_device = ALIASES.device_type_aliases.get(dType.lower(), DEVICE_TYPE.deviceStrings[device_type])

            imagePath = langImagePath.replace('{device_type}', replace_device)
            logging.info('Looking for images at ' + imagePath)

            for i in indexes:
                realImagePath = imagePath.replace("{index}", str(i))
                self.uploadScreenshot(device_type, realImagePath)
            self._images[device_type] = self.imagesForDevice(device_type)

        formData[formNames['version number']] = newAppMetadata['version']
        formData[formNames['copyright']] = newAppMetadata['copyright']
        formData[formNames['primary category']] = metadata.categories[newAppMetadata['primary category']]

        if metadata.subcategories != None and len(metadata.subcategories) != 0:
            if 'primary subcategory 1' in newAppMetadata:
                formData[formNames['primary subcategory 1']] = metadata.subcategories[newAppMetadata['primary subcategory 1']]
            if 'primary subcategory 2' in newAppMetadata:
                formData[formNames['primary subcategory 2']] = metadata.subcategories[newAppMetadata['primary subcategory 2']]
            if 'secondary subcategory 1' in newAppMetadata:
                formData[formNames['secondary subcategory 1']] = metadata.subcategories[newAppMetadata['secondary subcategory 1']]
            if 'secondary subcategory 2' in newAppMetadata:
                formData[formNames['secondary subcategory 2']] = metadata.subcategories[newAppMetadata['secondary subcategory 2']]

        if 'secondary category' in newAppMetadata:
            formData[formNames['secondary category']] = metadata.categories[newAppMetadata['secondary category']]

        appRatings = metadata.appRatings

        for index, rating in enumerate(newAppMetadata['app rating']):
            formData[appRatings[index]['name']] = appRatings[index]['ratings'][rating]

        if 'eula text' in newAppMetadata:
            formData[formNames['eula text']] = dataFromStringOrFile(newAppMetadata['eula text'])
            if 'eula countries' in newAppMetadata:
                self.__manageCountries(metadata.eulaCountries, newAppMetadata['eula countries'], formData)

        formData[formNames['description']] = dataFromStringOrFile(newAppMetadata['description'])
        formData[formNames['keywords']] = dataFromStringOrFile(newAppMetadata['keywords'])
        formData[formNames['support url']] = newAppMetadata['support url']
        formData[formNames['marketing url']] = newAppMetadata.get('marketing url')
        formData[formNames['privacy policy url']] = newAppMetadata.get('privacy policy url')

        appReviewInfo = appDictionary['app review information']
        formData[formNames['first name']] = appReviewInfo['first name']
        formData[formNames['last name']] = appReviewInfo['last name']
        formData[formNames['email address']] = appReviewInfo['email address']
        formData[formNames['phone number']] = appReviewInfo['phone number']
        formData[formNames['review notes']] = dataFromStringOrFile(appReviewInfo.get('review notes'))
        formData[formNames['username']] = appReviewInfo.get('demo username')
        formData[formNames['password']] = appReviewInfo.get('demo password')

        finalPageTree = self._parser.parseTreeForURL(metadata.submitAction, method="POST", payload=formData)
        errors = self._parser.checkPageForErrors(finalPageTree)

        if errors != None and len(errors) != 0:
            for error in errors:
                logging.error(error)
        else:
            idText = finalPageTree.xpath("//div[@id='column-bg']/div/p/label[.='Apple ID']/../span/text()")
            if len(idText) > 0:
                logging.info('Successfully created application. ID: ' + idText[0])
