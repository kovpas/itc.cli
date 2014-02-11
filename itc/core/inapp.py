import re
import logging

import requests

from itc.parsers.inappparser import ITCInappParser
from itc.util import EnhancedFile
from itc.util import languages
from itc.conf import *

class ITCInappPurchase(object):
    createInappLink = None
    actionURLs = None
    supportedIAPTypes = ['Consumable', 'Non-Consumable', 'Free Subscription', 'Non-Renewing Subscription']

    def __init__(self, name=None, numericId=None, productId=None, iaptype=None, manageLink=None, appleId=None):
        self.name = name
        self.numericId = numericId
        self.productId = productId
        self.appleId = appleId
        self.type = iaptype
        self.reviewNotes = None
        self.clearedForSale = False
        self.hostingContentWithApple = False
        self.manageLink = manageLink
        self._parser = ITCInappParser()

        logging.info('Inapp found: ' + self.__str__())
        logging.debug('productId: ' + (self.productId if self.productId != None else ""))
        logging.debug('type: ' + (self.type if self.type != None else ""))
        logging.debug('manage link: ' + (self.manageLink if self.manageLink != None else ""))


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        strng = ""
        if self.name != None:
            strng += "\"" + self.name + "\""
        if self.numericId != None:
            strng += " (" + str(self.appleId) + ")"

        return strng

    def __uploadScreenshot(self, file_path):
        if self._uploadScreenshotAction == None or self._uploadScreenshotKey == None:
            raise 'Trying to upload screenshot without proper session keys'

        if os.path.exists(file_path):
            headers = { 'x-uploadKey' : self._uploadScreenshotKey
                        , 'x-uploadSessionID' : self._uploadSessionId
                        , 'x-original-filename' : os.path.basename(file_path)
                        , 'Content-Type': 'image/png'}
            logging.info('Uploading image ' + file_path)
            r = self._parser.requests_session.post(ITUNESCONNECT_URL + self._uploadScreenshotAction
                                , cookies=cookie_jar
                                , headers=headers
                                , data=EnhancedFile(file_path, 'rb'))

            if r.content == 'success':
                # newImages = self.__imagesForDevice(upload_type)
                # if len(newImages) > len(self._images[upload_type]):
                #     logging.info('Image uploaded')
                # else:
                #     logging.error('Upload failed: ' + file_path)
                pass

    def __createUpdateLanguage(self, localizationTree, langId, langVal, isEdit=False):
        langName = languages.languageNameForId(langId)
        localizationSaveAction = localizationTree.xpath('//div[@class="lcAjaxLightboxContents"]/@action')[0]
        languageSelect = None
        langSelectName = None
        langSelectValue = None
        langFormData = {}

        if isEdit == False:
            languageSelect = localizationTree.xpath('//select[@id="language-popup"]')[0]
            langSelectName = languageSelect.xpath('./@name')[0]
            langSelectValue = languageSelect.xpath('./option[.="' + langName + '"]/@value')[0]
            langFormData[langSelectName] = langSelectValue

        nameElementName = localizationTree.xpath('//div[@id="proposedDisplayName"]//input/@name')[0]
        descriptionElementName = localizationTree.xpath('//div[@id="proposedDescription"]//textarea/@name')[0]

        publicationName = localizationTree.xpath('//div[@id="proposedPublicationName"]//input/@name')
        if len(publicationName) > 0:
            publicationName = publicationName[0]
            langFormData[publicationName] = langVal['publication name']

        langFormData[nameElementName] = langVal['name']
        langFormData[descriptionElementName] = langVal['description']
        langFormData['save'] = "true"

        postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + localizationSaveAction, data = langFormData, cookies=cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            logging.error("Save information failed. " + postFormResponse.text)


    def generateConfig(self):
        tree = self._parser.parseTreeForURL(ITCInappPurchase.actionURLs['itemActionUrl'] + "?itemID=" + self.numericId)
        metadata = self._parser.metadataForInappPurchase(tree)

        inappDict = {"id": metadata.numericid, "_id": metadata.textid, "type": self.type
                    , "reference name": metadata.refname
                    , "price tier": metadata.price_tier
                    , "cleared": metadata.cleared
                    , "hosting content with apple": metadata.hosted
                    , "review notes": metadata.reviewnotes
                    , "languages": metadata.languages}

        return inappDict

    def update(self, inappDict):
        tree = self._parser.parseTreeForURL(ITCInappPurchase.actionURLs['itemActionUrl'] + "?itemID=" + self.numericId)

        # for non-consumable iap we can change name, cleared-for-sale and pricing. Check if we need to:
        inappReferenceName = tree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//span/text()')[0]
        clearedForSaleText = tree.xpath('//div[contains(@class,"cleared-for-sale")]//span/text()')[0]
        clearedForSale = False
        if clearedForSaleText == 'Yes':
            clearedForSale = True

        logging.debug('Updating inapp: ' + inappDict.__str__())

        self.name = inappDict.get('name', self.name)
        self.clearedForSale = inappDict.get('cleared', self.clearedForSale)
        self.hostingContentWithApple = inappDict.get('hosting content with apple', self.hostingContentWithApple)
        self.reviewNotes = inappDict.get('review notes', self.reviewNotes)

        # TODO: change price tier
        if (inappReferenceName != self.name) \
            or (clearedForSale != self.clearedForSale):
            editAction = tree.xpath('//div[@id="singleAddonPricingLightbox"]/@action')[0]

            inappTree = self._parser.parseTreeForURL(editAction)

            inappReferenceNameName = inappTree.xpath('//div[@id="referenceNameTooltipId"]/..//input/@name')[0]
            clearedForSaleName = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@name')[0]
            clearedForSaleNames = {}
            clearedForSaleNames["true"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@value')[0]
            clearedForSaleNames["false"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioFalse"]/@value')[0]
            inappPriceTierName = inappTree.xpath('//select[@id="price_tier_popup"]/@name')[0]

            dateComponentsNames = inappTree.xpath('//select[contains(@id, "_day")]/@name')
            dateComponentsNames.extend(inappTree.xpath('//select[contains(@id, "_month")]/@name'))
            dateComponentsNames.extend(inappTree.xpath('//select[contains(@id, "_year")]/@name'))

            postAction = inappTree.xpath('//div[@class="lcAjaxLightboxContents"]/@action')[0]

            formData = {}
            formData[inappReferenceNameName] = self.name
            formData[clearedForSaleName] = clearedForSaleNames["true" if self.clearedForSale else "false"]
            formData[inappPriceTierName] = 'WONoSelectionString'
            for dcn in dateComponentsNames:
                formData[dcn] = 'WONoSelectionString'
            formData['save'] = "true"

            postFormResponse = self._parser.requests_session.post(ITUNESCONNECT_URL + postAction, data = formData, cookies=cookie_jar)

            if postFormResponse.status_code != 200:
                raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)


        idAddon = "autoRenewableL" if (inapptype == "Free Subscription") else "l"
        languagesSpan = inappTree.xpath('//span[@id="0' + idAddon + 'ocalizationListListRefreshContainerId"]')[0]
        activatedLanguages = languagesSpan.xpath('.//li[starts-with(@id, "0' + idAddon + 'ocalizationListRow")]/div[starts-with(@class, "ajaxListRowDiv")]/@itemid')
        activatedLangsIds = [languages.langCodeForLanguage(lang) for lang in activatedLanguages]
        languageAction = tree.xpath('//div[@id="0' + idAddon + 'ocalizationListLightbox"]/@action')[0]

        logging.info('Activated languages for inapp ' + self.numericId + ': ' + ', '.join(activatedLanguages))
        logging.debug('Activated languages ids: ' + ', '.join(activatedLangsIds))

        langDict = inappDict.get('languages', {})
        for langId, langVal in langDict.items():
            if type(langVal) is str:
                if langId in activatedLangsIds and langVal == 'd': # TODO: delete lang
                    pass
                return
            
            languageParamStr = ""
            isEdit = False

            if langId in activatedLangsIds: # edit
                languageParamStr = "&itemID=" + languages.appleLangIdForLanguage(langId)
                isEdit = True

            localizationTree = self._parser.parseTreeForURL(languageAction + "?open=true" + languageParamStr)
            self.__createUpdateLanguage(localizationTree, langId, langVal, isEdit=isEdit)

        # upload screenshot, edit review notes, hosting content with apple, etc
        formData = {"save":"true"}
        editHostedContentAction = tree.xpath('//div[@id="versionLightboxId0"]/@action')[0]
        hostedContentTree = self._parser.parseTreeForURL(editHostedContentAction + "?open=true")
        saveEditHostedContentAction = hostedContentTree.xpath('//div[@class="lcAjaxLightboxContents"]/@action')[0]

        if (self.type == "Non-Consumable"):
            hostingContentName = hostedContentTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@name')[0]
            hostingContentNames = {}
            hostingContentNames["true"] = hostedContentTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@value')[0]
            hostingContentNames["false"] = hostedContentTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioFalse"]/@value')[0]
            formData[hostingContentName] = hostingContentNames["true" if self.hostingContentWithApple else "false"]

        if inappDict['review screenshot'] != None:
            uploadForm = hostedContentTree.xpath('//form[@name="FileUploadForm__screenshotId"]')[0]
            self._uploadScreenshotAction = uploadForm.xpath('./@action')[0]
            self._uploadSessionId = uploadForm.xpath('.//input[@id="uploadSessionID"]/@value')[0]
            self._uploadScreenshotKey = uploadForm.xpath('.//input[@id="uploadKey"]/@value')[0]
            statusURLScript = hostedContentTree.xpath('//script[contains(., "var uploader_screenshotId")]/text()')[0]
            matches = re.findall('statusURL:\s\'([^\']+)\'', statusURLScript)
            self._statusURL = matches[0]
            self.__uploadScreenshot(inappDict['review screenshot'])
            self._parser.requests_session.get(ITUNESCONNECT_URL + self._statusURL, cookies=cookie_jar)

            formData["uploadSessionID"] = self._uploadSessionId
            formData["uploadKey"] = self._uploadScreenshotKey
            formData["filename"] = inappDict['review screenshot']

 
        reviewNotesName = hostedContentTree.xpath('//div[@class="hosted-review-notes"]//textarea/@name')[0]
        formData[reviewNotesName] = self.reviewNotes
        self._parser.parseTreeForURL(saveEditHostedContentAction, method="POST", payload=formData)


    def create(self, langDict, screenshot=None):
        logging.debug('Creating inapp: ' + langDict.__str__())

        tree = self._parser.parseTreeForURL(ITCInappPurchase.createInappLink)

        inapptype = self.type
        newInappLink = tree.xpath('//form[@name="mainForm"]/@action')[0]
        newInappTypeLink = tree.xpath('//div[@class="type-section"]/h3[.="' + inapptype + '"]/following-sibling::a/@href')[0]
        
        inappTree = self._parser.parseTreeForURL(newInappTypeLink, method="GET")

        if ITCInappPurchase.actionURLs == None:
            inappsActionScript = inappTree.xpath('//script[contains(., "var arguments")]/text()')[0]
            matches = re.findall('\'([^\']+)\'\s:\s\'([^\']+)\'', inappsActionScript)
            ITCInappPurchase.actionURLs = dict((k, v) for k, v in matches if k.endswith('Url'))

        formData = {}

        inappReferenceNameName = inappTree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//input/@name')[0]
        inappProductIdName = inappTree.xpath('//div[@id="productIdText"]//input/@name')[0]
        clearedForSaleName = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@name')[0]
        clearedForSaleNames = {}
        clearedForSaleNames["true"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@value')[0]
        clearedForSaleNames["false"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioFalse"]/@value')[0]

        if (inapptype != "Free Subscription"):
            inappPriceTierName = inappTree.xpath('//select[@id="price_tier_popup"]/@name')[0]
            formData[inappPriceTierName] = int(self.priceTier)

        if (inapptype == "Non-Consumable"):
            hostingContentName = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@name')[0]
            hostingContentNames = {}
            hostingContentNames["true"] = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@value')[0]
            hostingContentNames["false"] = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioFalse"]/@value')[0]
            formData[hostingContentName] = hostingContentNames["true" if self.hostingContentWithApple else "false"]

        reviewNotesName = inappTree.xpath('//div[@id="reviewNotesCreation"]//textarea/@name')[0]

        if (inapptype == "Free Subscription"):
            localizationLightboxAction = inappTree.xpath('//div[@id="autoRenewableLocalizationListLightbox"]/@action')[0]
        else:
            localizationLightboxAction = inappTree.xpath('//div[@id="localizationListLightbox"]/@action')[0]

        for langId, langVal in langDict.items():
            localizationTree = self._parser.parseTreeForURL(localizationLightboxAction + "?open=true")

            self.__createUpdateLanguage(localizationTree, langId, langVal)

        if screenshot != None:
            uploadForm = inappTree.xpath('//form[@name="FileUploadForm__screenshotId"]')[0]
            self._uploadScreenshotAction = uploadForm.xpath('./@action')[0]
            self._uploadSessionId = uploadForm.xpath('.//input[@id="uploadSessionID"]/@value')[0]
            self._uploadScreenshotKey = uploadForm.xpath('.//input[@id="uploadKey"]/@value')[0]
            statusURLScript = inappTree.xpath('//script[contains(., "var uploader_screenshotId")]/text()')[0]
            matches = re.findall('statusURL:\s\'([^\']+)\'', statusURLScript)
            self._statusURL = matches[0]
            self.__uploadScreenshot(screenshot)
            self._parser.requests_session.get(ITUNESCONNECT_URL + self._statusURL, cookies=cookie_jar)

            formData["uploadSessionID"] = self._uploadSessionId
            formData["uploadKey"] = self._uploadScreenshotKey
            formData["filename"] = screenshot

        postAction = inappTree.xpath('//form[@id="addInitForm"]/@action')[0]

        formData[inappReferenceNameName] = self.name
        formData[inappProductIdName] = self.productId
        formData[clearedForSaleName] = clearedForSaleNames["true" if self.clearedForSale else "false"]
        formData[reviewNotesName] = self.reviewNotes

        self._parser.parseTreeForURL(postAction, method="POST", payload=formData)
        postFormTree = self._parser.parseTreeForURL(newInappLink, method="POST", payload=formData)
        errorDiv = postFormTree.xpath('//div[@id="LCPurpleSoftwarePageWrapperErrorMessage"]')

        if len(errorDiv) > 0:
            logging.error("Save information failed. " + errorDiv[0].xpath('.//span/text()')[0])

