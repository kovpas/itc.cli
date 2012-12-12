import os
import sys
import re
import urllib2
import json
import logging
import languages
from collections import namedtuple

import requests
from lxml import etree
from lxml.html import tostring
import html5lib

ITUNESCONNECT_URL = 'https://itunesconnect.apple.com'

def getElement(list, index):
    try:
        return list[index]
    except Exception:
        return ""

class ITCInappPurchase(object):
    createInappLink = None
    actionURLs = None
    __parser = None

    def __init__(self, name=None, numericId=None, productId=None, iaptype=None, manageLink=None, cookie_jar=None):
        self.name = name
        self.numericId = numericId
        self.productId = productId
        self.type = iaptype
        self.reviewNotes = None
        self.clearedForSale = False
        self.hostingContentWithApple = False
        self.manageLink = manageLink
        self._cookie_jar = cookie_jar

        if ITCInappPurchase.__parser == None:
            ITCInappPurchase.__parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)


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
            strng += " (" + str(self.numericId) + ")"

        return strng

    def update(self, langDict):
        createInappsResponse = requests.get(ITUNESCONNECT_URL + ITCInappPurchase.actionURLs['itemActionUrl'] + "?itemID=" + self.numericId, cookies = self._cookie_jar)

        if createInappsResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(createInappsResponse.status_code)

        tree = ITCInappPurchase.__parser.parse(createInappsResponse.text)

        # for non-consumable iap we can change name, cleared-for-sale and pricing. Check if we need to:
        inappReferenceName = tree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//span/text()')[0]
        clearedForSaleText = tree.xpath('//div[contains(@class,"cleared-for-sale")]//span/text()')[0]
        clearedForSale = False
        if clearedForSaleText == 'Yes':
            clearedForSale = True

        # TODO: change price tier
        if (inappReferenceName != self.name) or (clearedForSale != self.clearedForSale):
            editAction = tree.xpath('//div[@id="singleAddonPricingLightbox"]/@action')[0]

            editInappsResponse = requests.get(ITUNESCONNECT_URL + editAction, cookies = self._cookie_jar)

            if editInappsResponse.status_code != 200:
                raise 'Wrong response from iTunesConnect. Status code: ' + str(editInappsResponse.status_code)

            inappTree = ITCInappPurchase.__parser.parse(editInappsResponse.text)

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

            postFormResponse = requests.post(ITUNESCONNECT_URL + postAction, data = formData, cookies = self._cookie_jar)

            if postFormResponse.status_code != 200:
                raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)


    def create(self, langDict):
        createInappsResponse = requests.get(ITUNESCONNECT_URL + ITCInappPurchase.createInappLink, cookies = self._cookie_jar)

        if createInappsResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(createInappsResponse.status_code)

        tree = ITCInappPurchase.__parser.parse(createInappsResponse.text)

        inapptype = self.type
        newInappLink = tree.xpath('//form[@name="mainForm"]/@action')[0]
        formKeyName = tree.xpath('//div[@class="type-section"]/h3[.="' + inapptype + '"]/following-sibling::input/@name')[0]
        
        formData = {formKeyName + '.x': 46, formKeyName + '.y': 10}
        createInappResponse = requests.post(ITUNESCONNECT_URL + newInappLink, data=formData, cookies=self._cookie_jar)
        inappTree = ITCInappPurchase.__parser.parse(createInappResponse.text)

        if createInappResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(createInappResponse.status_code)

        if ITCInappPurchase.actionURLs == None:
            inappsActionScript = inappTree.xpath('//script[contains(., "var arguments")]/text()')[0]
            matches = re.findall('\'([^\']+)\'\s:\s\'([^\']+)\'', inappsActionScript)
            ITCInappPurchase.actionURLs = dict((k, v) for k, v in matches if k.endswith('Url'))

        inappReferenceNameName = inappTree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//input/@name')[0]
        inappProductIdName = inappTree.xpath('//div[@id="productIdText"]//input/@name')[0]
        clearedForSaleName = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@name')[0]
        clearedForSaleNames = {}
        clearedForSaleNames["true"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioTrue"]/@value')[0]
        clearedForSaleNames["false"] = inappTree.xpath('//div[contains(@class,"cleared-for-sale")]//input[@classname="radioFalse"]/@value')[0]
        inappPriceTierName = inappTree.xpath('//select[@id="price_tier_popup"]/@name')[0]
        hostingContentName = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@name')[0]
        hostingContentNames = {}
        hostingContentNames["true"] = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioTrue"]/@value')[0]
        hostingContentNames["false"] = inappTree.xpath('//div[contains(@class,"hosting-on-apple")]//input[@classname="radioFalse"]/@value')[0]
        reviewNotesName = inappTree.xpath('//div[@id="reviewNotesCreation"]//textarea/@name')[0]

        localizationLightboxAction = inappTree.xpath('//div[@id="localizationListLightbox"]/@action')[0]

        for langId, langVal in langDict.items():
            createInappLocalizationResponse = requests.get(ITUNESCONNECT_URL + localizationLightboxAction + "?open=true", cookies=self._cookie_jar)
            if createInappResponse.status_code != 200:
                raise 'Wrong response from iTunesConnect. Status code: ' + str(createInappResponse.status_code)

            langName = languages.languageNameForId(langId)
            localizationTree = ITCInappPurchase.__parser.parse(createInappLocalizationResponse.text)
            localizationSaveAction = localizationTree.xpath('//div[@class="lcAjaxLightboxContents"]/@action')[0]
            languageSelect = localizationTree.xpath('//select[@id="language-popup"]')[0]
            langSelectName = languageSelect.xpath('./@name')[0]
            langSelectValue = languageSelect.xpath('./option[.="' + langName + '"]/@value')[0]
            nameElementName = localizationTree.xpath('//div[@id="proposedDisplayName"]//input/@name')[0]
            descriptionElementName = localizationTree.xpath('//div[@id="proposedDescription"]//textarea/@name')[0]

            langFormData = {}
            langFormData[langSelectName] = langSelectValue
            langFormData[nameElementName] = langVal['name']
            langFormData[descriptionElementName] = langVal['description']
            langFormData['save'] = "true"
            
            postFormResponse = requests.post(ITUNESCONNECT_URL + localizationSaveAction, data = langFormData, cookies = self._cookie_jar)

            if postFormResponse.status_code != 200:
                raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

            if len(postFormResponse.text) > 0:
                logging.error("Save information failed. " + postFormResponse.text)

        postAction = inappTree.xpath('//form[@id="addInitForm"]/@action')[0]

        formData = {}
        formData[inappReferenceNameName] = self.name
        formData[inappProductIdName] = self.productId
        formData[clearedForSaleName] = clearedForSaleNames["true" if self.clearedForSale else "false"]
        formData[inappPriceTierName] = int(self.priceTier) - 1
        formData[hostingContentName] = hostingContentNames["true" if self.hostingContentWithApple else "false"]
        formData[reviewNotesName] = self.reviewNotes

        postFormResponse = requests.post(ITUNESCONNECT_URL + postAction, data = formData, cookies = self._cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        createInappResponse = requests.post(ITUNESCONNECT_URL + newInappLink, data=formData, cookies=self._cookie_jar)
        postFormTree = ITCInappPurchase.__parser.parse(postFormResponse.text)
        errorDiv = postFormTree.xpath('//div[@id="LCPurpleSoftwarePageWrapperErrorMessage"]')

        if len(errorDiv) > 0:
            logging.error("Save information failed. " + errorDiv[0].xpath('.//span/text()')[0])

