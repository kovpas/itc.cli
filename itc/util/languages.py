import json
import logging

languages_map = {}

def __parse_languages_map():
    try:
        try:
             import pkgutil
             data = pkgutil.get_data(__name__, 'languages.json')
        except ImportError:
             import pkg_resources
             data = pkg_resources.resource_string(__name__, 'languages.json')
        globals()['languages_map'] = json.loads(data)
    except BaseException:
        raise 

def __langs():
    if globals()['languages_map'] == None or len(globals()['languages_map']) == 0:
        __parse_languages_map()
        logging.debug(globals()['languages_map'])

    return globals()['languages_map']

def appleLangIdForLanguage(languageString):
    """
    returns apple language id (i.e. 'French_CA') for language name 
    (i.e. 'Canadian French') or code (i.e. 'fr-CA')
    """
    lang = __langs().get(languageString)
    if lang != None:
        if type(lang) is dict:
            return lang['name']

        return lang

    for langId, lang in __langs().items():
        if type(lang) is dict:
            if lang['name'] == languageString:
                return lang['id']
        else:
            if lang == languageString:
                return lang
                
    return None

def langCodeForLanguage(languageString):
    """
    returns language code (i.e. 'fr-CA') for language name 
    (i.e. 'Canadian French') or apple language id (i.e. 'French_CA')
    """
    for langId, lang in __langs().items():
        if type(lang) is dict:
            if (lang['name'] == languageString) or (lang['id'] == languageString):
                return langId
        else:
            if lang == languageString:
                return langId
                
    return None

def languageNameForId(languageId):
    lang = __langs()[languageId]
    if type(lang) is dict:
        return lang['name']

    return lang
