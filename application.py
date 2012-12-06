import os
import sys

class ITCApplication(object):
    def __init__(self, name=None, applicationId=None, link=None, dict=None):
        if (dict):
            name = dict['name']
            link = dict['applicationLink']
            applicationId = dict['applicationId']

        self.name = name
        self.applicationLink = link
        self.applicationId = applicationId

    def __repr__(self):
        return self.__str__()

    def reprJSON(self):
        return dict(name = self.name, applicationId = self.applicationId, applicationLink = self.applicationLink)

    def __str__(self):
        str = ""
        if self.name != None:
            str += "\"" + self.name + "\""
        if self.applicationId != None:
            str += " (" + self.applicationId + ")"
        # if self.applicationLink != None:
        #     str += ": " + self.applicationLink

        return str