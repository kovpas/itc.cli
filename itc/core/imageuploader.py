# coding=utf-8

import re
import json
import logging

import requests

from itc.util import EnhancedFile
from itc.conf import *

class ITCImageUploader(object):
    _uploadSessionData = None
    _images = None
    def __init__(self):
        self._uploadSessionData = {}
        self._images = {}

    def parseURLSFromScript(self, script):
        matches = re.search('{.*statusURL:\s\'([^\']+)\',\sdeleteURL:\s\'([^\']+)\',\ssortURL:\s\'([^\']+)\'', script) 
        return {'statusURL': matches.group(1)
                , 'deleteURL': matches.group(2)
                , 'sortURL': matches.group(3)}

    def parseStatusURLSFromScript(self, script):
        matches = re.search('{.*statusURL:\s\'([^\']+)\'', script) 
        return {'statusURL': matches.group(1)}

    def imagesForDevice(self, device_type):
        if len(self._uploadSessionData) == 0:
            raise 'No session keys found'

        statusURL = self._uploadSessionData[device_type]['statusURL']
        result = None

        if statusURL:
            attempts = 3
            while attempts > 0 and result == None:
                status = self._parser.requests_session.get(ITUNESCONNECT_URL + statusURL
                                      , cookies=cookie_jar)
                statusJSON = None
                try:
                    statusJSON = json.loads(status.content)
                except ValueError:
                    logging.error('Can\'t parse status content. New attempt (%d of %d)' % (4 - attempts), attempts)
                    attempts -= 1
                    continue

                logging.debug(status.content)
                result = []

                for i in range(0, 5):
                    key = 'pictureFile_' + str(i + 1)
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


    def uploadScreenshot(self, upload_type, file_path):
        if self._uploadSessionId == None or len(self._uploadSessionData) == 0:
            raise 'Trying to upload screenshot without proper session keys'

        uploadScreenshotAction = self._uploadSessionData[upload_type]['action']
        uploadScreenshotKey = self._uploadSessionData[upload_type]['key']

        if uploadScreenshotAction != None and uploadScreenshotKey != None and os.path.exists(file_path):
            headers = { 'x-uploadKey' : uploadScreenshotKey
                        , 'x-uploadSessionID' : self._uploadSessionId
                        , 'x-original-filename' : os.path.basename(file_path)
                        , 'Content-Type': 'image/png'}
            logging.info('Uploading image ' + file_path)
            r = self._parser.requests_session.post(ITUNESCONNECT_URL + uploadScreenshotAction
                                , cookies=cookie_jar
                                , headers=headers
                                , data=EnhancedFile(file_path, 'rb'))

            if r.content == 'success':
                newImages = self.imagesForDevice(upload_type)
                if len(newImages) > len(self._images[upload_type]):
                    logging.info('Image uploaded')
                else:
                    logging.error('Upload failed: ' + file_path)


    def deleteScreenshot(self, type, screenshot_id):
        if len(self._uploadSessionData) == 0:
            raise 'Trying to delete screenshot without proper session keys'

        deleteScreenshotAction = self._uploadSessionData[type]['deleteURL']
        if deleteScreenshotAction != None:
            self._parser.requests_session.get(ITUNESCONNECT_URL + deleteScreenshotAction + "?pictureId=" + screenshot_id
                    , cookies=cookie_jar)

            # TODO: check status


    def sortScreenshots(self, type, newScreenshotsIndexes):
        if len(self._uploadSessionData) == 0:
            raise 'Trying to sort screenshots without proper session keys'

        sortScreenshotsAction = self._uploadSessionData[type]['sortURL']

        if sortScreenshotsAction != None:
            self._parser.requests_session.get(ITUNESCONNECT_URL + sortScreenshotsAction 
                                    + "?sortedIDs=" + (",".join(newScreenshotsIndexes))
                            , cookies=cookie_jar)

            # TODO: check status
