import os
import sys
import re
import urllib2
import json

import requests
from lxml import etree
from lxml.html import tostring
import html5lib

ITUNESCONNECT_URL = 'https://itunesconnect.apple.com'

class UPLOAD_TYPE:
    iPad = 0
    iPhone = 1
    iPhone5 = 2

class EnhancedFile(file):
    def __init__(self, *args, **keyws):
        file.__init__(self, *args, **keyws)

    def __len__(self):
        return int(os.fstat(self.fileno())[6])

class ITCApplication(object):
    def __init__(self, name=None, applicationId=None, link=None, dict=None, cookie_jar=None):
        if (dict):
            print dict
            name = dict['name']
            link = dict['applicationLink']
            applicationId = dict['applicationId']

        self.name = name
        self.applicationLink = link
        self.applicationId = applicationId
        self.versions = {}
        self._uploadSessionData = {}
        self._images = {}

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

    def __parseURLSFromScript(self, script):
        matches = re.search('{.*statusURL:\s\'([^\']+)\',\sdeleteURL:\s\'([^\']+)\',\ssortURL:\s\'([^\']+)\'', script) 
        return {'statusURL': matches.group(1)
                , 'deleteURL': matches.group(2)
                , 'sortURL': matches.group(3)}

    def __imagesForDevice(self, device_type):
        if len(self._uploadSessionData) == 0:
            raise 'No session keys found'

        statusURL = self._uploadSessionData[device_type]['statusURL']
        result = None

        if statusURL:
            status = requests.get(ITUNESCONNECT_URL + statusURL
                                  , cookies=self._cookie_jar)
            statusJSON = json.loads(status.content)
            result = []

            for i in range(1, 5):
                key = 'pictureFile_' + str(i)
                if key in statusJSON:
                    image = {}
                    pictureFile = statusJSON[key]
                    image['url'] = pictureFile['url']
                    image['orientation'] = pictureFile['orientation']
                    image['id'] = pictureFile['pictureId']
                    result.append(image)
                else:
                    break

        return result


    def __uploadScreenshot(self, upload_type, file_path):
        if self._uploadSessionId == None or len(self._uploadSessionData) == 0:
            raise 'Trying to upload screenshot without proper session keys'

        uploadScreenshotAction = self._uploadSessionData[upload_type]['action']
        uploadScreenshotKey = self._uploadSessionData[upload_type]['key']

        if uploadScreenshotAction != None and uploadScreenshotKey != None and os.path.exists(file_path):
            headers = { 'x-uploadKey' : uploadScreenshotKey
                        , 'x-uploadSessionID' : self._uploadSessionId
                        , 'x-original-filename' : os.path.basename(file_path)
                        , 'Content-Type': 'image/png'}
            print 'Uploading image ' + file_path
            r = requests.post(ITUNESCONNECT_URL + uploadScreenshotAction
                                , cookies=self._cookie_jar
                                , headers=headers
                                , data=EnhancedFile(file_path, 'rb'))

            if r.content == 'success':
                newImages = self.__imagesForDevice(upload_type)
                if len(newImages) > len(self._images[upload_type]):
                    print 'Image uploaded'
                else:
                    print 'Something\'s wrong...' 


    def __deleteScreenshot(self, type, screenshot_id):
        if len(self._uploadSessionData) == 0:
            raise 'Trying to delete screenshot without proper session keys'

        deleteScreenshotAction = self._uploadSessionData[type]['deleteURL']
        if deleteScreenshotAction != None:
            r = requests.get(ITUNESCONNECT_URL + deleteScreenshotAction + "?pictureId=" + screenshot_id
                    , cookies=self._cookie_jar)

            # TODO: check status


    def __sortScreenshots(self, type, newScreenshotsIndexes):
        if len(self._uploadSessionData) == 0:
            raise 'Trying to sort screenshots without proper session keys'

        sortScreenshotsAction = self._uploadSessionData[type]['sortURL']

        if sortScreenshotsAction != None:
            r = requests.get(ITUNESCONNECT_URL + sortScreenshotsAction + "?sortedIDs=" + (",".join(newScreenshotsIndexes))
                    , cookies=self._cookie_jar)

    def editVersion(self, dataDict, versionString=None):
        if dataDict == None or len(dataDict) == 0: # nothing to change
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
        hasWhatsNew = False

        submitAction = editTree.xpath("//div[@class='lcAjaxLightboxContentsWrapper']/div[@class='lcAjaxLightboxContents']/@action")[0]

        appNameName     = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@name")[0]
        descriptionName = editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/@name")[0]
        whatsNewName    = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/@name")

        if len(whatsNewName) > 0: # there's no what's new section for first version
            hasWhatsNew = True
            whatsNewName = whatsNewName[0]

        keywordsName     = editTree.xpath("//div/label[.='Keywords']/..//input/@name")[0]
        supportURLName   = editTree.xpath("//div/label[.='Support URL']/..//input/@name")[0]
        marketingURLName = editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@name")[0]
        pPolicyURLName   = editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@name")[0]

        appNameValue     = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@value")[0]
        descriptionValue = editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/text()")[0]
        whatsNewValue    = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/text()")

        if len(whatsNewValue) > 0 and hasWhatsNew:
            whatsNewValue = whatsNewValue[0]

        keywordsValue     = editTree.xpath("//div/label[.='Keywords']/..//input/@value")[0]
        supportURLValue   = editTree.xpath("//div/label[.='Support URL']/..//input/@value")[0]
        marketingURLValue = editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@value")[0]
        pPolicyURLValue   = editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@value")[0]

        formData = {}
        formData[appNameName] = appNameValue
        formData[descriptionName] = descriptionValue
        if hasWhatsNew:
            formData[whatsNewName] = whatsNewValue

        formData[keywordsName] = keywordsValue
        formData[supportURLName] = supportURLValue
        formData[marketingURLName] = marketingURLValue
        formData[pPolicyURLName] = pPolicyURLValue
        formData["save"] = "true"

        if 'name' in dataDict:
            formData[descriptionName] = dataDict['name']

        if 'description' in dataDict:
            formData[appNameName] = dataDict['description']

        if hasWhatsNew and 'whats new' in dataDict:
            formData[whatsNewName] = dataDict['whats new']

        if 'keywords' in dataDict:
            formData[keywordsName] = dataDict['keywords']

        if 'support url' in dataDict:
            formData[supportURLName] = dataDict['support url']

        if 'marketing url' in dataDict:
            formData[marketingURLName] = dataDict['marketing url']

        if 'privacy policy url' in dataDict:
            formData[pPolicyURLName] = dataDict['privacy policy url']

        iphoneUploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_35InchRetinaDisplayScreenshots']")[0]
        iphone5UploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_iPhone5']")[0]
        ipadUploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_iPadScreenshots']")[0]

        iphoneUploadScreenshotJS = iphoneUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        iphone5UploadScreenshotJS = iphone5UploadScreenshotForm.xpath('../following-sibling::script/text()')[0]
        ipadUploadScreenshotJS = ipadUploadScreenshotForm.xpath('../following-sibling::script/text()')[0]

        self._uploadSessionData[UPLOAD_TYPE.iPhone] = dict({'action': iphoneUploadScreenshotForm.attrib['action']
                                                        , 'key': iphoneUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                      }, **self.__parseURLSFromScript(iphoneUploadScreenshotJS))
        self._uploadSessionData[UPLOAD_TYPE.iPhone5] = dict({'action': iphone5UploadScreenshotForm.attrib['action']
                                                         , 'key': iphone5UploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                       }, **self.__parseURLSFromScript(iphone5UploadScreenshotJS))
        self._uploadSessionData[UPLOAD_TYPE.iPad] = dict({'action': ipadUploadScreenshotForm.attrib['action']
                                                      , 'key': ipadUploadScreenshotForm.xpath(".//input[@name='uploadKey']/@value")[0]
                                                    }, **self.__parseURLSFromScript(ipadUploadScreenshotJS))

        self._uploadSessionId = iphoneUploadScreenshotForm.xpath('.//input[@name="uploadSessionID"]/@value')[0]

        # get all images
        for device_type in [UPLOAD_TYPE.iPhone, UPLOAD_TYPE.iPhone5, UPLOAD_TYPE.iPad]:
            self._images[device_type] = self.__imagesForDevice(device_type)

        print self._images

        newList = [elem['id'] for elem in self._images[UPLOAD_TYPE.iPhone5]] 
        newList[0], newList[1] = newList[1], newList[0]
        self.__sortScreenshots(UPLOAD_TYPE.iPhone5, newList)

        if False:
            image_path = 'images/en/iphone 5 1.png'
            self.__deleteScreenshot(UPLOAD_TYPE.iPhone5, self._images[UPLOAD_TYPE.iPhone5][1]['id'])
            self.__uploadScreenshot(UPLOAD_TYPE.iPhone5, image_path)

        formData['uploadSessionID'] = self._uploadSessionId
        # formData['uploadKey'] = self._uploadSessionData[UPLOAD_TYPE.iPhone5]['key']

        postFormResponse = requests.post(ITUNESCONNECT_URL + submitAction, data = formData, cookies = self._cookie_jar)

        if postFormResponse.status_code != 200:
            raise 'Wrong response from iTunesConnect. Status code: ' + str(postFormResponse.status_code)

        if len(postFormResponse.text) > 0:
            print "Error: " + postFormResponse.text
