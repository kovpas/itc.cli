import os
import sys

import requests
from lxml import etree
from lxml.html import tostring
import html5lib

ITUNESCONNECT_URL = 'https://itunesconnect.apple.com'

class ITCApplication(object):
    def __init__(self, name=None, applicationId=None, link=None, dict=None, cookie_jar=None):
        if (dict):
            name = dict['name']
            link = dict['applicationLink']
            applicationId = dict['applicationId']

        self.name = name
        self.applicationLink = link
        self.applicationId = applicationId
        self.versions = {}

        self._cookie_jar = cookie_jar


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        strng = ""
        if self.name != None:
            strng += "\"" + self.name + "\""
        if self.applicationId != None:
            strng += " (" + str(self.applicationId) + ")"
        # if self.applicationLink != None:
        #     strng += ": " + self.applicationLink

        return strng


    def getVersions(self):
        if self.applicationLink == None:
            raise 'Can\'t get application versions'

        appVersionsResponse = requests.get(ITUNESCONNECT_URL + self.applicationLink, cookies = self._cookie_jar)

        if appVersionsResponse.status_code != 200:
            raise 'Can\'t get application versions'

        parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
        tree = parser.parse(appVersionsResponse.text)
        versionsContainer = tree.xpath("//h2[.='Versions']/following-sibling::div")
        if len(versionsContainer) == 0:
            return

        versionDivs = versionsContainer[0].xpath(".//div[@class='version-container']")
        if len(versionDivs) == 0:
            return

        for versionDiv in versionDivs:
            version = {}
            versionString = versionDiv.xpath(".//p/label[.='Version']/../span")[0].text.strip()
            
            version['detailsLink'] = versionDiv.xpath(".//span[.='View Details']/..")[0].attrib['href']
            version['statusString'] = ("".join([str(x) for x in versionDiv.xpath(".//span/img[starts-with(@src, '/itc/images/status-')]/../text()")])).strip()
            version['editable'] = (version['statusString'] != 'Ready for Sale')
            version['versionString'] = versionString

            self.versions[versionString] = version


    def editVersion(self, dataDict, versionString=None):
        if len(dataDict) == 0: # nothing to change
            return

        if len(self.versions) == 0:
            self.getVersions()

        if len(self.versions) == 0:
            raise 'Can\'t get application\'s versions'

        if versionString == None: # Suppose there's one or less editable versions
            versionString = next((versionString for versionString, version in self.versions.items() if version['editable']), None)

        if versionString == None: # Suppose there's one or less editable versions
            raise 'No editable version found'
            
        version = self.versions[versionString]
        if not version['editable']:
            raise 'Version ' + versionString + ' is not editable'

        appVersionResponse = requests.get(ITUNESCONNECT_URL + version['detailsLink'], cookies = self._cookie_jar)

        if appVersionResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(appVersionResponse.status_code)

        parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
        tree = parser.parse(appVersionResponse.text)
        localizationLightboxAction = tree.xpath("//div[@id='localizationLightbox']/@action")[0]

        print 'Enter edit mode for version ' + versionString

        editResponse = requests.get(ITUNESCONNECT_URL + localizationLightboxAction + "?open=true", cookies = self._cookie_jar)

        # versionDataContainer = tree.xpath("//span[@id='localizationLightboxUpdate']")

        if editResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(editResponse.status_code)

        editTree = parser.parse(editResponse.text)

        submitAction = editTree.xpath("//div[@class='lcAjaxLightboxContentsWrapper']/div[@class='lcAjaxLightboxContents']/@action")[0]

        appNameName     = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@name")[0]
        descriptionName = editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/@name")[0]
        whatsNewName    = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/@name")[0]

        keywordsName     = editTree.xpath("//div/label[.='Keywords']/..//input/@name")[0]
        supportURLName   = editTree.xpath("//div/label[.='Support URL']/..//input/@name")[0]
        marketingURLName = editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@name")[0]
        pPolicyURLName   = editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@name")[0]

        appNameValue     = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@value")[0]
        descriptionValue = editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/text()")[0]
        whatsNewValue    = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/text()")[0]

        keywordsValue     = editTree.xpath("//div/label[.='Keywords']/..//input/@value")[0]
        supportURLValue   = editTree.xpath("//div/label[.='Support URL']/..//input/@value")[0]
        marketingURLValue = editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@value")[0]
        pPolicyURLValue   = editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@value")[0]

        formData = {}
        formData[appNameName] = appNameValue
        formData[descriptionName] = descriptionValue
        formData[whatsNewName] = whatsNewValue
        formData[keywordsName] = keywordsValue
        formData[supportURLName] = supportURLValue
        formData[marketingURLName] = marketingURLValue
        formData[pPolicyURLName] = pPolicyURLValue
        formData["save"] = "true"

        if hasattr(dataDict,'name'):
            formData[descriptionName] = dataDict['name']

        if hasattr(dataDict,'description'):
            formData[appNameName] = dataDict['description']

        if hasattr(dataDict,'whats new'):
            formData[whatsNewName] = dataDict['whats new']

        if hasattr(dataDict,'keywords'):
            formData[keywordsName] = dataDict['keywords']

        if hasattr(dataDict,'support url'):
            formData[supportURLName] = dataDict['support url']

        if hasattr(dataDict,'marketing url'):
            formData[marketingURLName] = dataDict['marketing url']

        if hasattr(dataDict,'privacy policy url'):
            formData[pPolicyURLName] = dataDict['privacy policy url']

        print formData

        postFormResponse = requests.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies = self._cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            print "Error: " + postFormResponse.text
