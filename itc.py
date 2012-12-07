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
    parser.add_argument('--config_file', '-c', dest='config_file', required=True,
                       help='Configuration file. For more details on format see https://github.com/kovpas/itc.cli')
    parser.add_argument('--debug', '-d', dest='debug', default=False, action='store_true',
                       help='Debug output')

    args = parser.parse_args(args)
    globals()["options"] = args

    if args.debug == True:
        logging.basicConfig(level=logging.DEBUG)

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
    else:
        raise 'Can\'t read config file' 

    return globals()['config']


def main():
    origcwd = os.path.abspath(os.getcwd())

    if 'APPDATA' in os.environ:
        homepath = os.environ['APPDATA']
    elif 'HOME' in os.environ:
        homepath = os.environ["HOME"]
    else:
        homepath = ''

    # If we end up creating a cookie file, make sure it's only readable by the
    # user.
    os.umask(0077)

    # Load the config and cookie files
    cookie_file = os.path.join(homepath, ".itc-cli-cookies.txt")
    storage_file = os.path.join(homepath, ".itc-cli-storage.txt")

    args = parse_options(sys.argv[1:])
    
    logging.debug('Python %s' % sys.version)
    logging.debug('Running on %s' % (platform.platform()))
    logging.debug('Home = %s' % homepath)
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
    applicationId = cfg['application id']
    application = None
    commonActions = cfg['commands']
    specificLangCommands = commonActions['languages']
    commonActions['languages'] = None
    langActions = {}

    for lang in specificLangCommands:
        langActions[languages.languageNameForId(lang)] = dict_merge(commonActions, specificLangCommands[lang])
        break

    logging.debug(langActions)

    if applicationId in server.applications:
        application = server.applications[applicationId]
        for lang in langActions:
            actions = langActions[lang]
            application.editVersion(actions, lang=lang)


if __name__ == "__main__":
    main()