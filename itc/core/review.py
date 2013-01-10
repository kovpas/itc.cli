# coding=utf-8

import logging

from itc.util import languages
from itc.conf import *

class ITCReview(object):
    def __init__(self, reviewId=None, authorName=None, text=None, store=None, rating=0, date=None):
        self.reviewId = reviewId
        self.authorName = authorName
        self.text = text
        self.store = store
        self.rating = rating
        self.date = date

        logging.debug('Review: ' + self.__str__())


    def __repr__(self):
        return self.__str__()


    def __str__(self):
        return self.authorName + " (" + self.store + ", " + self.date + ") " + str(self.rating) + "\n" + self.text

