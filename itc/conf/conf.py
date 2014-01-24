import os
from tempfile import gettempdir
from cookielib import LWPCookieJar

ITUNESCONNECT_URL = 'https://itunesconnect.apple.com'
ITUNESCONNECT_MAIN_PAGE_URL = '/WebObjects/iTunesConnect.woa'
KEYRING_SERVICE_NAME = 'itc.cli'

class DEVICE_TYPE:
    iPad = 0
    iPhone = 1
    iPhone5 = 2
    deviceStrings = ['iPad', 'iPhone', 'iPhone 5']

temp_dir = gettempdir()
default_file_format = 'images/{language}/{device_type} {index}.png'
cookie_file_name = '.itc-cli-cookies.txt'
cookie_file = os.path.join(temp_dir, cookie_file_name)
cookie_jar = LWPCookieJar(cookie_file)

class ALIASES:
    language_aliases = {}
    device_type_aliases = {}

class config:
    options = {}

def __initCookies():
    if cookie_file:
        try:
            cookie_jar.load(cookie_file, ignore_discard=True)
        except IOError:
            pass

__initCookies()