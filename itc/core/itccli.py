"""Command line interface for iTunesConnect (https://github.com/kovpas/itc.cli)

Usage: 
    itc login [-n] [-k | -w] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc update -c FILE [-a APP_ID] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc version -c FILE [-a APP_ID] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc create -c FILE [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc generate [-a APP_ID] [-e APP_VER] [-i] [-c FILE] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s]
    itc promo -a APP_ID [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s] [-o FILE] <amount>
    itc reviews -a APP_ID [-d DATE] [-l] [-n] [-k] [-u USERNAME] [-p PASSWORD] [-z] [-v | -vv [-f] | -s] [-o FILE]
    itc (-h | --help)

Commands:
  login                       Logs in with specified credentials.
  update                      Update specified app with information provided in a config file.
  create                      Creates new app using information provided in a config file.
  generate                    Generate configuration file for a specified application id and version.
                                If no --application-id provided, configuration files for all 
                                applications will be created.
  promo                       Download specified <amount> of promocodes.
  reviews                     Get reviews for a specified application.

Options:
  --version                   Show version.
  -h --help                   Print help (this message) and exit.
  -v --verbose                Verbose mode. Enables debug print to console.
  -vv                         Enables HTTP response print to a console.
  -f                          Nicely format printed html response.
  -s --silent                 Silent mode. Only error messages are printed.
  -u --username USERNAME      iTunesConnect username.
  -p --password PASSWORD      iTunesConnect password.
  -e --application-version APP_VER  
                              Application version to generate config.
                                If not provided, config will be generated for latest version.
  -i --generate-config-inapp  Generate config for inapps as well.
  -c --config-file FILE       Configuration file. For more details on format see https://github.com/kovpas/itc.cli.
  -a --application-id APP_ID  Application id to process. This property has more priority than 'application id'
                                in configuration file.
  -n --no-cookies             Remove saved authentication cookies and authenticate again.
  -k --store-password         Store password in a system's secure storage. Removes authentication cookies first, so password has to be entered manually.
  -w --delete-password        Remove stored password system's secure storage.
  -z                          Automatically click 'Continue' button if appears after login.
  -o --output-file FILE       Name of file to save promocodes or reviews to.
  -d --date-range DATERANGE   Get reviews specified with this date range. Format [date][-][date].
                                For more information, please, refer to https://github.com/kovpas/itc.cli.
  -l --latest-version         Get reviews for current version only.

"""

import os
import logging
import colorer
import platform
import sys
import json
import getpass
import keyring
from copy import deepcopy 

from itc.core.server import ITCServer
from itc.core import __version__
from itc.util import *
from itc.conf import *
from docopt import docopt

options = None
config = {}

def __parse_options():
    args = docopt(__doc__, version=__version__)
    conf.config.options = args
    globals()['options'] = args
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if args['--verbose']:
        logging.basicConfig(level=logging.DEBUG, format=log_format)
    elif not args['--silent']:
        requests_log = logging.getLogger('requests')
        requests_log.setLevel(logging.WARNING)
        
        logging.basicConfig(level=logging.INFO, format=log_format)
    else:
        requests_log = logging.getLogger('requests')
        requests_log.setLevel(logging.ERROR)
        
        logging.basicConfig(level=logging.ERROR, format=log_format)

    return args

def __parse_configuration_file():
    if options['--config-file'] != None:
        with open(options['--config-file']) as config_file:
            globals()['config'] = json.load(config_file)
        ALIASES.language_aliases = globals()['config'].get('config', {}) \
                                .get('language aliases', {})
        ALIASES.device_type_aliases = globals()['config'].get('config', {}) \
                                .get('device type aliases', {})

    return globals()['config']


def flattenDictIndexes(dict):
    for indexKey, val in dict.items():
        if "-" in indexKey:
            startIndex, endIndex = indexKey.split("-")
            for i in range(int(startIndex), int(endIndex) + 1):
                dict[i] = val
            del dict[indexKey]
        else: 
            try:
                dict[int(indexKey)] = val
                del dict[indexKey]
            except:
                pass

    return dict


def main():
    os.umask(0077)
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir);

    args = __parse_options()

    logging.debug('Python %s' % sys.version)
    logging.debug('Running on %s' % platform.platform())
    logging.debug('Temp path = %s' % temp_dir)
    logging.debug('Current Directory = %s' % os.getcwd())

    logging.debug('args %s' % args)

    if options['--no-cookies'] or options['--store-password']:
        logging.debug('Deleting cookie file: ' + cookie_file)
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
            cookie_jar.clear()
            logging.info('Removed authentication cookies')
        else:
            logging.debug('Cookie file doesn\'t exist')

    if options['--username'] == None:
        options['--username'] = raw_input('Username: ')

    if options['--delete-password']:
        keyring.delete_password(KEYRING_SERVICE_NAME, options['--username'])

    if options['--password'] == None:
        logging.debug('Looking for password in a secure storage. Username: ' + options['--username'])
        options['--password'] = keyring.get_password(KEYRING_SERVICE_NAME, options['--username'])

    server = ITCServer(options['--username'], options['--password'])

    if not server.isLoggedIn:
        if options['--password'] == None:
            options['--password'] = getpass.getpass()
        server.login(password = options['--password'])

    if server.isLoggedIn and options['--store-password']:
        keyring.set_password(KEYRING_SERVICE_NAME, options['--username'], options['--password'])

    if len(server.applications) == 0:
        server.fetchApplicationsList()

    if len(server.applications) == 0:
        logging.info('No applications found.')
        return
        
    logging.debug(server.applications)
    if options['--application-id']:
        options['--application-id'] = int(options['--application-id'])


    if options['generate']:
        if options['--application-id']:
            if options['--application-id'] in server.applications: 
                applications = {}
                applications[options['--application-id']] = server.applications[options['--application-id']]
            else:
                logging.error('No application with id ' + str(options['--application-id']))
                return
        else:
            applications = server.applications

        for applicationId, application in applications.items():
            updatedApplication = server.getApplicationById(applicationId)
            updatedApplication.generateConfig(options['--application-version'], generateInapps = options['--generate-config-inapp'])

        return

    if options['promo']:
        if not options['--application-id'] in server.applications: 
            logging.error("Provide correct application id (--application-id or -a option)")
        else:
            application = server.getApplicationById(options['--application-id'])
            promocodes = application.getPromocodes(options['<amount>'])
            if options['--output-file']:
                with open(options['--output-file'], 'a') as outFile:
                    outFile.write(promocodes)
            else: # just print to console. Using print as we want to suppress silence option
                print promocodes

        return

    if options['reviews']:
        if not options['--application-id'] in server.applications: 
            logging.error("Provide correct application id (--application-id or -a option)")
        else:
            application = server.getApplicationById(options['--application-id'])
            application.generateReviews(options['--latest-version'], options['--date-range'], options['--output-file'])

        return

    cfg = __parse_configuration_file()
    if len(cfg) == 0:
        logging.info('Nothing to do.')
        return

    applicationDict = cfg['application']
    applicationId = applicationDict.get('id', -1)
    if options['--application-id']:
        applicationId = int(options['--application-id'])
    application = None
    commonActions = applicationDict.get('metadata', {}).get('general', {})
    specificLangCommands = applicationDict.get('metadata', {}).get('languages', {})
    langActions = {}
    filename_format = cfg.get('config', {}) \
                           .get('images', {}) \
                              .get('file name format', default_file_format)

    for lang in specificLangCommands:
        langActions[languages.languageNameForId(lang)] = dict_merge(commonActions, specificLangCommands[lang])

    logging.debug(langActions)

    if applicationId not in server.applications and not options['create']:
        logging.warning('No application with id ' + str(applicationId))
        choice = raw_input('Do you want to create a new one? [y/n]')
        options['create'] = True if choice.strip().lower() in ('y', 'yes', '') else False

    if options['create']:
        server.createNewApp(applicationDict, filename_format=filename_format)
    elif applicationId in server.applications:
        application = server.getApplicationById(applicationId)
        if options['version']:
            langActions['default'] = commonActions
            application.addVersion(applicationDict['version'], langActions)
        else:
            for lang in langActions:
                actions = langActions[lang]
                application.editVersion(actions, lang=lang, filename_format=filename_format)

            appReviewInfo = applicationDict.get('app review information', None)

            if appReviewInfo != None:
                application.editReviewInformation(appReviewInfo)

            for inappDict in applicationDict.get('inapps', {}):
                isIterable = inappDict['id'].find('{index}') != -1
                iteratorDict = inappDict.get('index iterator')

                if isIterable and (iteratorDict == None):
                    logging.error('Inapp id contains {index} keyword, but no index_iterator object found. Skipping inapp: ' + inappDict['id'])
                    continue

                langsDict = inappDict['languages']
                genericLangsDict = inappDict['general']

                for langId in langsDict:
                    langsDict[langId] = dict_merge(genericLangsDict, langsDict[langId])

                inappDict['languages'] = langsDict
                del inappDict['general']

                indexes = [-1]
                if (isIterable):
                    indexes = iteratorDict.get('indexes')
                    if indexes == None:
                        indexes = range(iteratorDict.get('from', 1), iteratorDict['to'] + 1)

                if iteratorDict != None:
                    del inappDict['index iterator']

                for key, value in inappDict.items():
                    if (not key in ("index iterator", "general", "languages")) and isinstance(value, dict):
                        flattenDictIndexes(value)

                for langKey, value in inappDict["languages"].items():
                    for innerLangKey, langValue in inappDict["languages"][langKey].items():
                        if isinstance(langValue, dict):
                            flattenDictIndexes(langValue)

                realindex = 0
                for index in indexes:
                    inappIndexDict = deepcopy(inappDict)
                    if isIterable:
                        for key in inappIndexDict:
                            if key in ("index iterator", "general", "languages"):
                                continue

                            if (isinstance(inappIndexDict[key], basestring)):
                                inappIndexDict[key] = inappIndexDict[key].replace('{index}', str(index))
                            elif (isinstance(inappIndexDict[key], list)):
                                inappIndexDict[key] = inappIndexDict[key][realindex]
                            elif (isinstance(inappIndexDict[key], dict)):
                                inappIndexDict[key] = inappIndexDict[key][index]

                        langsDict = inappIndexDict['languages']

                        for langId, langDict in langsDict.items():
                            for langKey in langDict:
                                if (isinstance(langDict[langKey], basestring)):
                                    langDict[langKey] = langDict[langKey].replace('{index}', str(index))
                                elif (isinstance(langDict[langKey], list)):
                                    langDict[langKey] = langDict[langKey][realindex]
                                elif (isinstance(langDict[langKey], dict)):
                                    langDict[langKey] = langDict[langKey][index]

                    inapp = application.getInappById(inappIndexDict['id'])
                    if inapp == None:
                        application.createInapp(inappIndexDict)
                    else:
                        inapp.update(inappIndexDict)

                    realindex += 1
    else:
        logging.error('No application with id ' + str(applicationId))
        return

