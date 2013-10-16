import os
import json 
from copy import deepcopy 
from itc.conf import ALIASES

def getElement(list, index, outOfBoundsValue=""):
    """
    Safe get element from a list. If index is out of bounds, return outOfBoundsValue
    """
    try:
        return list[index]
    except Exception:
        return outOfBoundsValue

def dict_merge(a, b):
    """
    recursively merges dict's. not just simple a['key'] = b['key'], if
    both a and b have a key who's value is a dict then dict_merge is called
    on both values and the result stored in the returned dictionary.
    """
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
                result[k] = dict_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result

def dataFromStringOrFile(value, languageCode=None):
    if (isinstance(value, basestring)):
        return value
    elif (isinstance(value, dict)):
        if ('file name format' in value):
            descriptionFilePath = value['file name format']
            if languageCode != None:
                replace_language = ALIASES.language_aliases.get(languageCode, languageCode)
                descriptionFilePath = descriptionFilePath.replace('{language}', replace_language)
            return open(descriptionFilePath, 'r').read()

    return ""

class EnhancedFile(file):
    def __init__(self, *args, **keyws):
        file.__init__(self, *args, **keyws)

    def __len__(self):
        return int(os.fstat(self.fileno())[6])

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'__dict__'):
            return obj.__dict__
        else:
            return None

