#!/usr/bin/env python

import cookielib
import os
import argparse
import logging
import platform
import sys
import json
import getpass

from server import ITCServer 

options = None
config = {}
languages_map = {}

def debug(s):
    if options and options.debug:
        print ">>> %s" % s

def parse_options(args):
    parser = argparse.ArgumentParser(description='Command line interface for iTunesConnect.')
    parser.add_argument('--username', dest='username',
                       help='iTunesConnect username')
    parser.add_argument('--password', dest='password',
                       help='iTunesConnect password')
    parser.add_argument('--config_file', dest='config_file',
                       help='Configuration file. For more details on format see https://github.com/kovpas/itc.cli')
    parser.add_argument('--debug', '-d', dest='debug', default=False, action='store_true',
                       help='run script in debug mode')

    args = parser.parse_args(args)
    globals()["options"] = args

    return args


def parse_configuration_file():
    if options.config_file != None and os.path.exists(options.config_file):
        fp = open(options.config_file)
        config = json.load(fp)
        fp.close()

    return config


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
    
    debug('Python %s' % sys.version)
    debug('Running on %s' % (platform.platform()))
    debug('Home = %s' % homepath)
    debug('Current Directory = %s' % os.getcwd())

    debug('args %s' % args)

    if options.username == None:
        options.username = raw_input('Username: ')

    server = ITCServer(options, cookie_file, storage_file)

    if not server.isLoggedIn:
        if options.password == None:
            options.password = getpass.getpass()
        server.login()

    if len(server.applications) == 0:
        server.getApplicationsList()
        
    print server.applications

    cfg = parse_configuration_file()
    applicationId = cfg['application id']
    application = None
    actions = cfg['commands']

    if applicationId in server.applications:
        application = server.applications[applicationId]
        application.editVersion(actions)
        # languages = 


if __name__ == "__main__":
    main()