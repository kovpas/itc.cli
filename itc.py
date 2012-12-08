#!/usr/bin/env python

import cookielib
import os
import argparse
import logging
import platform
import sys
import json
import getpass
import logging

from server import ITCServer 
from copy import deepcopy 
import languages

options = None
config = {}

def parse_options(args):
    parser = argparse.ArgumentParser(description='Command line interface for iTunesConnect.')
    parser.add_argument('--username', '-u', dest='username',
                       help='iTunesConnect username')
    parser.add_argument('--password', '-p', dest='password',
                       help='iTunesConnect password')
    parser.add_argument('--config_file', '-c', dest='config_file',
                       help='Configuration file. For more details on format see https://github.com/kovpas/itc.cli')
    parser.add_argument('--debug', '-d', dest='debug', default=False, action='store_true',
                       help='Debug output')

    args = parser.parse_args(args)
    globals()["options"] = args

    if args.debug == True:
        logging.basicConfig(level=logging.DEBUG)
    else:
        requests_log = logging.getLogger("requests")
        requests_log.setLevel(logging.WARNING)
        
        logging.basicConfig(level=logging.INFO)

    return args


def dict_merge(a, b):
    '''recursively merges dict's. not just simple a['key'] = b['key'], if
    both a and b have a key who's value is a dict then dict_merge is called
    on both values and the result stored in the returned dictionary.'''
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
                result[k] = dict_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result

def parse_configuration_file():
    if options.config_file != None and os.path.exists(options.config_file):
        fp = open(options.config_file)
        globals()['config'] = json.load(fp)
        fp.close()

    return globals()['config']


def main():
    os.umask(0077)
    scriptDir = os.path.dirname(os.path.realpath(__file__))

    # Load the config and cookie files
    cookie_file = os.path.join(scriptDir, ".itc-cli-cookies.txt")
    storage_file = os.path.join(scriptDir, ".itc-cli-storage.txt")

    args = parse_options(sys.argv[1:])
    
    logging.debug('Python %s' % sys.version)
    logging.debug('Running on %s' % (platform.platform()))
    logging.debug('Script path = %s' % scriptDir)
    logging.debug('Current Directory = %s' % os.getcwd())

    logging.debug('args %s' % args)

    logging.debug(languages.langs())

    if options.username == None:
        options.username = raw_input('Username: ')

    server = ITCServer(options, cookie_file, storage_file)

    if not server.isLoggedIn:
        if options.password == None:
            options.password = getpass.getpass()
        server.login()

    if len(server.applications) == 0:
        server.getApplicationsList()
        
    logging.debug(server.applications)

    cfg = parse_configuration_file()
    if len(cfg) == 0:
        logging.info('Nothing to do.')
        return

    applicationId = cfg['application id']
    application = None
    commonActions = cfg['commands']['general']
    specificLangCommands = cfg['commands']['languages']
    langActions = {}
    filename_format = cfg['config']['images']['filename_format']
    # filename_format = os.path.join('images', languageCode, DEVICE_TYPE.deviceStrings[device_type] + ' {index}.png')  

    for lang in specificLangCommands:
        langActions[languages.languageNameForId(lang)] = dict_merge(commonActions, specificLangCommands[lang])

    logging.debug(langActions)

    if applicationId in server.applications:
        application = server.applications[applicationId]
        for lang in langActions:
            actions = langActions[lang]
            application.editVersion(actions, lang=lang, filename_format=filename_format)


if __name__ == "__main__":
    main()