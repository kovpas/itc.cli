#!/usr/bin/env python

import cookielib
import os
import argparse
import logging
import platform
import re
import sys

from server import ITCServer 

options = None
configs = []

def debug(s):
    if options and options.debug:
        print ">>> %s" % s

def parse_options(args):
    parser = argparse.ArgumentParser(description='Command line interface for iTunesConnect.')
    parser.add_argument('--username', dest='username',
                       help='iTunesConnect username')
    parser.add_argument('--password', dest='password',
                       help='iTunesConnect password')
    parser.add_argument('--debug', '-d', dest='debug', default=False, action='store_true',
                       help='run script in debug mode')

    args = parser.parse_args(args)
    globals()["options"] = args

    return args

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

    args = parse_options(sys.argv[1:])
    # options.debug = True

    debug('Python %s' % sys.version)
    debug('Running on %s' % (platform.platform()))
    debug('Home = %s' % homepath)
    debug('Current Directory = %s' % os.getcwd())

    debug('args %s' % args)

    if options.username == None:
        options.username = raw_input('Username: ')

    if options.password == None:
        options.passowrd = raw_input('Password: ')

    server = ITCServer(options, cookie_file)

    server.login()
    server.getApplicationsList()

if __name__ == "__main__":
    main()