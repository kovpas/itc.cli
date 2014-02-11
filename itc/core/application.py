# coding=utf-8

import os
import re
import json
import logging
import sys
import codecs
from datetime import datetime, timedelta

import requests

from itc.core.inapp import ITCInappPurchase
from itc.core.imageuploader import ITCImageUploader
from itc.parsers.applicationparser import ITCApplicationParser
from itc.util import languages
from itc.util import dataFromStringOrFile
from itc.util import EnhancedFile
from itc.util import getElement
from itc.conf import *

class ITCApplication(ITCImageUploader):
    def __init__(self, name=None, applicationId=None, link=None, dict=None):
        if (dict):
            name = dict['name']
            link = dict['applicationLink']
            applicationId = dict['applicationId']

        self.name = name
        self.applicationLink = link
        self.applicationId = applicationId
        self.versions = {}
        self.inapps = {}

        self._manageInappsLink = None
        self._customerReviewsLink = None
        self._addVersionLink = None
        self._manageInappsTree = None
        self._createInappLink = None
        self._inappActionURLs = None
        self._parser = ITCApplicationParser()

        logging.info('Application found: ' + self.__str__())
        super(ITCApplication, self).__init__()


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        strng = ""
        if self.name != None:
            strng += "\"" + self.name + "\""
        if self.applicationId != None:
            strng += " (" + str(self.applicationId) + ")"

        return strng


    def getAppInfo(self):
        if self.applicationLink == None:
            raise 'Can\'t get application versions'

        tree = self._parser.parseTreeForURL(self.applicationLink)
        versionsMetadata = self._parser.parseAppVersionsPage(tree)
        # get 'manage in-app purchases' link
        self._manageInappsLink = versionsMetadata.manageInappsLink
        self._customerReviewsLink = versionsMetadata.customerReviewsLink
        self._addVersionLink = versionsMetadata.addVersionLink
        self.versions = versionsMetadata.versions


    def __parseAppVersionMetadata(self, version, language=None):
        tree = self._parser.parseTreeForURL(version['detailsLink'])

        return self._parser.parseCreateOrEditPage(tree, version, language)

    def __parseAppReviewInformation(self, version):
        tree = self._parser.parseTreeForURL(version['detailsLink'])

        return self._parser.parseAppReviewInfoForm(tree)

    def __generateConfigForVersion(self, version):
        languagesDict = {}

        metadata = self.__parseAppVersionMetadata(version)
        formData = metadata.formData
        # activatedLanguages = metadata.activatedLanguages

        for languageId, formValuesForLang in formData.items():
            langCode = languages.langCodeForLanguage(languageId)
            resultForLang = {}

            resultForLang["name"]               = formValuesForLang['appNameValue']
            resultForLang["description"]        = formValuesForLang['descriptionValue']
            resultForLang["whats new"]          = formValuesForLang.get('whatsNewValue')
            resultForLang["keywords"]           = formValuesForLang['keywordsValue']
            resultForLang["support url"]        = formValuesForLang['supportURLValue']
            resultForLang["marketing url"]      = formValuesForLang['marketingURLValue']
            resultForLang["privacy policy url"] = formValuesForLang['pPolicyURLValue']

            languagesDict[langCode] = resultForLang

        resultDict = {'config':{}, 'application': {'id': self.applicationId, 'metadata': {'general': {}, 'languages': languagesDict}}}

        return resultDict


    def generateConfig(self, versionString=None, generateInapps=False):
        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'
        if versionString == None: # Suppose there's one or less editable versions
            versionString = next((versionString for versionString, version in self.versions.items() if version['editable']), None)
        if versionString == None: # No versions to edit. Generate config from the first one
            versionString = self.versions.keys()[0]
        
        resultDict = self.__generateConfigForVersion(self.versions[versionString])

        if generateInapps:
            if len(self.inapps) == 0:
                self.getInapps()

            inapps = []
            for inappId, inapp in self.inapps.items():
                inapps.append(inapp.generateConfig())

            if len(inapps) > 0:
                resultDict['inapps'] = inapps

        filename = str(self.applicationId) + '.json'
        with open(filename, 'wb') as fp:
            json.dump(resultDict, fp, sort_keys=False, indent=4, separators=(',', ': '))


    def editVersion(self, dataDict, lang=None, versionString=None, filename_format=None):
        if dataDict == None or len(dataDict) == 0: # nothing to change
            return

        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'
        if versionString == None: # Suppose there's one or less editable versions
            versionString = next((versionString for versionString, version in self.versions.items() if version['editable']), None)
        if versionString == None: # Suppose there's one or less editable versions
            raise 'No editable version found'
            
        version = self.versions[versionString]
        if not version['editable']:
            raise 'Version ' + versionString + ' is not editable'

        languageId = languages.appleLangIdForLanguage(lang)
        languageCode = languages.langCodeForLanguage(lang)

        metadata = self.__parseAppVersionMetadata(version, lang)
        # activatedLanguages = metadata.activatedLanguages
        # nonactivatedLanguages = metadata.nonactivatedLanguages
        formData = {} #metadata.formData[languageId]
        formNames = metadata.formNames[languageId]
        submitAction = metadata.submitActions[languageId]
        
        formData["save"] = "true"

        formData[formNames['appNameName']]      = dataDict.get('name', metadata.formData[languageId]['appNameValue'])
        formData[formNames['descriptionName']]  = dataFromStringOrFile(dataDict.get('description', metadata.formData[languageId]['descriptionValue']), languageCode)
        if 'whatsNewName' in formNames:
            formData[formNames['whatsNewName']] = dataFromStringOrFile(dataDict.get('whats new', metadata.formData[languageId]['whatsNewValue']), languageCode)
        formData[formNames['keywordsName']]     = dataFromStringOrFile(dataDict.get('keywords', metadata.formData[languageId]['keywordsValue']), languageCode)
        formData[formNames['supportURLName']]   = dataDict.get('support url', metadata.formData[languageId]['supportURLValue'])
        formData[formNames['marketingURLName']] = dataDict.get('marketing url', metadata.formData[languageId]['marketingURLValue'])
        formData[formNames['pPolicyURLName']]   = dataDict.get('privacy policy url', metadata.formData[languageId]['pPolicyURLValue'])

        iphoneUploadScreenshotForm  = formNames['iphoneUploadScreenshotForm'] 
        iphone5UploadScreenshotForm = formNames['iphone5UploadScreenshotForm']
        ipadUploadScreenshotForm    = formNames['ipadUploadScreenshotForm']

        iphoneUploadScreenshotJS = iphoneUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        iphone5UploadScreenshotJS = iphone5UploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        ipadUploadScreenshotJS = ipadUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]

        self._uploadSessionData[DEVICE_TYPE.iPhone] = dict({'action': iphoneUploadScreenshotForm.attrib['action']
                                                        , 'key': iphoneUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                      }, **self.parseURLSFromScript(iphoneUploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPhone5] = dict({'action': iphone5UploadScreenshotForm.attrib['action']
                                                         , 'key': iphone5UploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                       }, **self.parseURLSFromScript(iphone5UploadScreenshotJS))
        self._uploadSessionData[DEVICE_TYPE.iPad] = dict({'action': ipadUploadScreenshotForm.attrib['action']
                                                      , 'key': ipadUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                    }, **self.parseURLSFromScript(ipadUploadScreenshotJS))

        self._uploadSessionId = iphoneUploadScreenshotForm.xpath('.//input[@name="uploadSessionID"]/@value')[0]

        # get all images
        for device_type in [DEVICE_TYPE.iPhone, DEVICE_TYPE.iPhone5, DEVICE_TYPE.iPad]:
            self._images[device_type] = self.imagesForDevice(device_type)

        logging.debug(self._images)
        # logging.debug(formData)

        if 'images' in dataDict:
            imagesActions = dataDict['images']
            languageCode = languages.langCodeForLanguage(lang)

            for dType in imagesActions:
                device_type = None
                if dType.lower() == 'iphone':
                    device_type = DEVICE_TYPE.iPhone
                elif dType.lower() == 'iphone 5':
                    device_type = DEVICE_TYPE.iPhone5
                elif dType.lower() == 'ipad':
                    device_type = DEVICE_TYPE.iPad
                else:
                    continue

                deviceImagesActions = imagesActions[dType]
                if deviceImagesActions == "":
                    continue

                for imageAction in deviceImagesActions:
                    imageAction.setdefault('cmd')
                    imageAction.setdefault('indexes')
                    cmd = imageAction['cmd']
                    indexes = imageAction['indexes']
                    replace_language = ALIASES.language_aliases.get(languageCode, languageCode)
                    replace_device = ALIASES.device_type_aliases.get(dType.lower(), DEVICE_TYPE.deviceStrings[device_type])

                    imagePath = filename_format.replace('{language}', replace_language) \
                           .replace('{device_type}', replace_device)
                    logging.debug('Looking for images at ' + imagePath)

                    if (indexes == None) and ((cmd == 'u') or (cmd == 'r')):
                        indexes = []
                        for i in range(0, 5):
                            realImagePath = imagePath.replace("{index}", str(i + 1))
                            logging.debug('img path: ' + realImagePath)
                            if os.path.exists(realImagePath):
                                indexes.append(i + 1)

                    logging.debug('indexes ' + indexes.__str__())
                    logging.debug('Processing command ' + imageAction.__str__())

                    if (cmd == 'd') or (cmd == 'r'): # delete or replace. To perform replace we need to delete images first
                        deleteIndexes = [img['id'] for img in self._images[device_type]]
                        if indexes != None:
                            deleteIndexes = [deleteIndexes[idx - 1] for idx in indexes]

                        logging.debug('deleting images ' + deleteIndexes.__str__())
                        
                        for imageIndexToDelete in deleteIndexes:
                            img = next(im for im in self._images[device_type] if im['id'] == imageIndexToDelete)
                            self.deleteScreenshot(device_type, img['id'])

                        self._images[device_type] = self.imagesForDevice(device_type)
                    
                    if (cmd == 'u') or (cmd == 'r'): # upload or replace
                        currentIndexes = [img['id'] for img in self._images[device_type]]

                        if indexes == None:
                            continue

                        indexes = sorted(indexes)
                        for i in indexes:
                            realImagePath = imagePath.replace("{index}", str(i))
                            if os.path.exists(realImagePath):
                                self.uploadScreenshot(device_type, realImagePath)

                        self._images[device_type] = self.imagesForDevice(device_type)

                        if cmd == 'r':
                            newIndexes = [img['id'] for img in self._images[device_type]][len(currentIndexes):]

                            if len(newIndexes) == 0:
                                continue

                            for i in indexes:
                                currentIndexes.insert(i - 1, newIndexes.pop(0))

                            self.sortScreenshots(device_type, currentIndexes)
                            self._images[device_type] = self.imagesForDevice(device_type)

                    if (cmd == 's'): # sort
                        if indexes == None or len(indexes) != len(self._images[device_type]):
                            continue
                        newIndexes = [self._images[device_type][i - 1]['id'] for i in indexes]

                        self.sortScreenshots(device_type, newIndexes)
                        self._images[device_type] = self.imagesForDevice(device_type)

        formData['uploadSessionID'] = self._uploadSessionId
        logging.debug(formData)
        # formData['uploadKey'] = self._uploadSessionData[DEVICE_TYPE.iPhone5]['key']

        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            logging.error("Save information failed. " + postFormResponse.text)

########## App Review Information management ##########

    def editReviewInformation(self, appReviewInfo):
        if appReviewInfo == None or len(appReviewInfo) == 0: # nothing to change
            return

        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'

        versionString = next((versionString for versionString, version in self.versions.items() if version['editable']), None)
        if versionString == None: # Suppose there's one or less editable versions
            raise 'No editable version found'
            
        version = self.versions[versionString]
        if not version['editable']:
            raise 'Version ' + versionString + ' is not editable'

        metadata = self.__parseAppReviewInformation(version)
        formData = {}
        formNames = metadata.formNames
        submitAction = metadata.submitAction
        
        formData["save"] = "true"

        formData[formNames['first name']]    = appReviewInfo.get('first name', metadata.formData['first name'])
        formData[formNames['last name']]     = appReviewInfo.get('last name', metadata.formData['last name'])
        formData[formNames['email address']] = appReviewInfo.get('email address', metadata.formData['email address'])
        formData[formNames['phone number']]  = appReviewInfo.get('phone number', metadata.formData['phone number'])
        formData[formNames['review notes']]  = dataFromStringOrFile(appReviewInfo.get('review notes', metadata.formData['review notes']))
        formData[formNames['username']]      = appReviewInfo.get('username', metadata.formData['username'])
        formData[formNames['password']]      = appReviewInfo.get('password', metadata.formData['password'])

        logging.debug(formData)
        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            logging.error("Save information failed. " + postFormResponse.text)

################## In-App management ##################

    def __parseInappActionURLsFromScript(self, script):
        matches = re.findall('\'([^\']+)\'\s:\s\'([^\']+)\'', script)
        self._inappActionURLs = dict((k, v) for k, v in matches if k.endswith('Url'))
        ITCInappPurchase.actionURLs = self._inappActionURLs

        return self._inappActionURLs


    def __parseInappsFromTree(self, refreshContainerTree):
        logging.debug('Parsing inapps response')
        inappULs = refreshContainerTree.xpath('.//li[starts-with(@id, "ajaxListRow_")]')

        if len(inappULs) == 0:
            logging.info('No In-App Purchases found')
            return None

        logging.debug('Found ' + str(len(inappULs)) + ' inapps')

        inappsActionScript = refreshContainerTree.xpath('//script[contains(., "var arguments")]/text()')
        if len(inappsActionScript) > 0:
            inappsActionScript = inappsActionScript[0]
            actionURLs = self.__parseInappActionURLsFromScript(inappsActionScript)
            inappsItemAction = actionURLs['itemActionUrl']

        inapps = {}
        for inappUL in inappULs:
            appleId = inappUL.xpath('./div/div[5]/text()')[0].strip()
            if self.inapps.get(appleId) != None:
                inapps[appleId] = self.inapps.get(appleId)
                continue

            iaptype = inappUL.xpath('./div/div[4]/text()')[0].strip()  
            if not (iaptype in ITCInappPurchase.supportedIAPTypes):
                continue

            numericId = inappUL.xpath('./div[starts-with(@class,"ajaxListRowDiv")]/@itemid')[0]
            name = inappUL.xpath('./div/div/span/text()')[0].strip()
            productId = inappUL.xpath('./div/div[3]/text()')[0].strip()
            manageLink = inappsItemAction + "?itemID=" + numericId
            inapps[appleId] = ITCInappPurchase(name=name, appleId=appleId, numericId=numericId, productId=productId, iaptype=iaptype, manageLink=manageLink)

        return inapps


    def getInapps(self):
        if self._manageInappsLink == None:
            self.getAppInfo()
        if self._manageInappsLink == None:
            raise 'Can\'t get "Manage In-App purchases link"'

        # TODO: parse multiple pages of inapps.
        tree = self._parser.parseTreeForURL(self._manageInappsLink)

        self._createInappLink = tree.xpath('//img[contains(@src, "btn-create-new-in-app-purchase.png")]/../@href')[0]
        if ITCInappPurchase.createInappLink == None:
            ITCInappPurchase.createInappLink = self._createInappLink

        refreshContainerTree = getElement(tree.xpath('//span[@id="ajaxListListRefreshContainerId"]/ul'), 0, None)
        if refreshContainerTree == None:
            self.inapps = {}
        else:
            self.inapps = self.__parseInappsFromTree(refreshContainerTree)


    def getInappById(self, inappId):
        if self._inappActionURLs == None:
            self.getInapps()

        if len(self.inapps) == 0:
            return None

        if type(inappId) is int:
            inappId = str(inappId)

        if self.inapps.get(inappId) != None:
            return self.inapps[inappId]

        if self._manageInappsTree == None:
            self._manageInappsTree = self._parser.parseTreeForURL(self._manageInappsLink)

        tree = self._manageInappsTree
        reloadInappsAction = tree.xpath('//span[@id="ajaxListListRefreshContainerId"]/@action')[0]
        searchAction = self._inappActionURLs['searchActionUrl']

        logging.info('Searching for inapp with id ' + inappId)

        searchResponse = self._parser.requests_session.get(ITUNESCONNECT_URL + searchAction + "?query=" + inappId, cookies=cookie_jar)

        if searchResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(searchResponse.status_code)

        statusJSON = json.loads(searchResponse.content)
        if statusJSON['totalItems'] <= 0:
            logging.warn('No matching inapps found! Search term: ' + inappId)
            return None

        inapps = self.__parseInappsFromTree(self._parser.parseTreeForURL(reloadInappsAction))

        if inapps == None:
            raise "Error parsing inapps"

        if len(inapps) == 1:
            return inapps[0]

        tmpinapps = []
        for numericId, inapp in inapps.items():
            if (inapp.numericId == inappId) or (inapp.productId == inappId):
                return inapp

            components = inapp.productId.partition(u'…')
            if components[1] == u'…': #split successful
                if inappId.startswith(components[0]) and inappId.endswith(components[2]):
                    tmpinapps.append(inapp)

        if len(tmpinapps) == 1:
            return tmpinapps[0]

        logging.error('Multiple inapps found for id (' + inappId + ').')
        logging.error(tmpinapps)

        # TODO: handle this situation. It is possible to avoid this exception by requesting
        # each result's page. Possible, but expensive :)
        raise 'Ambiguous search result.'


    def createInapp(self, inappDict):
        if self._createInappLink == None:
            self.getInapps()
        if self._createInappLink == None:
            raise 'Can\'t create inapp purchase'

        if not (inappDict['type'] in ITCInappPurchase.supportedIAPTypes):
            logging.error('Can\'t create inapp purchase: "' + inappDict['id'] + '" is not supported')
            return

        iap = ITCInappPurchase(name=inappDict['reference name']
                             , productId=inappDict['id']
                             , iaptype=inappDict['type'])
        iap.clearedForSale = inappDict['cleared']
        iap.priceTier = int(inappDict['price tier']) - 1
        iap.hostingContentWithApple = inappDict['hosting content with apple']
        iap.reviewNotes = inappDict['review notes']

        iap.create(inappDict['languages'], screenshot=inappDict.get('review screenshot'))

####################### Add version ########################

    def addVersion(self, version, langActions):
        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'

        if self._addVersionLink == None:
            raise 'Can\'t find \'Add Version\' link.'

        logging.info('Parsing \'Add Version\' page')
        tree = self._parser.parseTreeForURL(self._addVersionLink)
        metadata = self._parser.parseAddVersionPageMetadata(tree)
        formData = {metadata.saveButton + '.x': 46, metadata.saveButton + '.y': 10}
        formData[metadata.formNames['version']] = version
        defaultWhatsNew = langActions.get('default', {}).get('whats new', '')
        logging.debug('Default what\'s new: ' + defaultWhatsNew.__str__())
        for lang, taName in metadata.formNames['languages'].items():
            languageCode = languages.langCodeForLanguage(lang)
            whatsNew = langActions.get(lang, {}).get('whats new', defaultWhatsNew)
            
            if (isinstance(whatsNew, dict)):
                whatsNew = dataFromStringOrFile(whatsNew, languageCode)
            formData[taName] = whatsNew
        self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.submitAction, data = formData, cookies=cookie_jar)

        # TODO: Add error handling


################## Promo codes management ##################

    def getPromocodes(self, amount):
        if len(self.versions) == 0:
            self.getAppInfo()
        if len(self.versions) == 0:
            raise 'Can\'t get application versions'

        # We need non-editable version to get promocodes from
        versionString = next((versionString for versionString, version in self.versions.items() if version['statusString'] == "Ready for Sale"), None)
        if versionString == None:
            raise 'No "Ready for Sale" versions found'
            
        version = self.versions[versionString]
        if version['editable']:
            raise 'Version ' + versionString + ' is editable.'

        #get promocodes link
        logging.info('Getting promocodes link')
        tree = self._parser.parseTreeForURL(version['detailsLink'])
        promocodesLink = self._parser.getPromocodesLink(tree)
        logging.debug('Promocodes link: ' + promocodesLink)

        #enter number of promocodes
        logging.info('Requesting promocodes: ' + amount)
        tree = self._parser.parseTreeForURL(promocodesLink)
        metadata = self._parser.parsePromocodesPageMetadata(tree)
        formData = {metadata.continueButton + '.x': 46, metadata.continueButton + '.y': 10}
        formData[metadata.amountName] = amount
        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.submitAction, data = formData, cookies=cookie_jar)

        #accept license agreement
        logging.info('Accepting license agreement')
        metadata = self._parser.parsePromocodesLicenseAgreementPage(postFormResponse.text)
        formData = {metadata.continueButton + '.x': 46, metadata.continueButton + '.y': 10}
        formData[metadata.agreeTickName] = metadata.agreeTickName
        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.submitAction, data = formData, cookies=cookie_jar)

        #download promocodes
        logging.info('Downloading promocodes')
        downloadCodesLink = self._parser.getDownloadCodesLink(postFormResponse.text)
        codes = self._parser.requests_session.get(ITUNESCONNECT_URL + downloadCodesLink
                                      , cookies=cookie_jar)

        return codes.text

################## Reviews management ##################
    def _parseDate(self, date):
        returnDate = None
        if date == 'today':
            returnDate = datetime.today()
        elif date == 'yesterday':
            returnDate = datetime.today() - timedelta(1)
        elif not '/' in date:
            returnDate = datetime.today() - timedelta(int(date))
        else:
            returnDate = datetime.strptime(date, '%d/%m/%Y')

        return datetime(returnDate.year, returnDate.month, returnDate.day)

    def generateReviews(self, latestVersion=False, date=None, outputFileName=None):
        if self._customerReviewsLink == None:
            self.getAppInfo()
        if self._customerReviewsLink == None:
            raise 'Can\'t get "Customer Reviews link"'

        minDate = None
        maxDate = None
        if date:
            if not '-' in date:
                minDate = self._parseDate(date)
                maxDate = minDate
            else:
                dateArray = date.split('-')
                if len(dateArray[0]) > 0:
                    minDate = self._parseDate(dateArray[0])
                if len(dateArray[1]) > 0:
                    maxDate = self._parseDate(dateArray[1])
                if maxDate != None and minDate != None and maxDate < minDate:
                    tmpDate = maxDate
                    maxDate = minDate
                    minDate = tmpDate

        logging.debug('From: %s' %minDate)
        logging.debug('To: %s' %maxDate)
        tree = self._parser.parseTreeForURL(self._customerReviewsLink)
        metadata = self._parser.getReviewsPageMetadata(tree)
        if (latestVersion):
            tree = self._parser.parseTreeForURL(metadata.currentVersion)
        else:
            tree = self._parser.parseTreeForURL(metadata.allVersions)
        tree = self._parser.parseTreeForURL(metadata.allReviews)

        reviews = {}
        logging.info('Fetching reviews for %d countries. Please wait...' % len(metadata.countries))
        percentDone = 0
        percentStep = 100.0 / len(metadata.countries)
        totalReviews = 0
        for countryName, countryId in metadata.countries.items():
            logging.debug('Fetching reviews for ' + countryName)
            formData = {metadata.countriesSelectName: countryId}
            postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + metadata.countryFormSubmitAction, data = formData, cookies=cookie_jar)
            reviewsForCountry = self._parser.parseReviews(postFormResponse.content, minDate=minDate, maxDate=maxDate)
            if reviewsForCountry != None and len(reviewsForCountry) != 0:
                reviews[countryName] = reviewsForCountry
                totalReviews = totalReviews + len(reviewsForCountry)
            if not config.options['--silent'] and not config.options['--verbose']:
                percentDone = percentDone + percentStep
                print >> sys.stdout, "\r%d%%" %percentDone,
                sys.stdout.flush()

        if not config.options['--silent'] and not config.options['--verbose']:
            print >> sys.stdout, "\rDone\n",
            sys.stdout.flush()

        logging.info("Got %d reviews." % totalReviews)

        if outputFileName:
            with codecs.open(outputFileName, 'w', 'utf-8') as fp:
                json.dump(reviews, fp, sort_keys=False, indent=4, separators=(',', ': '), ensure_ascii=False)
        else:
            print str(reviews).decode('unicode-escape')
