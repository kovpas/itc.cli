import os
import sys

class ITCApplication(object):
    def __init__(self, name, applicationId, link):
    	self.name = name
    	self.applicationLink = link
    	self.applicationId = applicationId

    	print self.name
    	print self.applicationId
    	print self.applicationLink