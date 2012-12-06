import os
import sys
import json

from cookielib import LWPCookieJar

import requests
from lxml import etree
from lxml.html import tostring
import html5lib

from application import ITCApplication 

ITUNESCONNECT_URL = 'https://itunesconnect.apple.com'
ITUNESCONNECT_MAIN_PAGE_URL = '/WebObjects/iTunesConnect.woa'

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'reprJSON'):
            return obj.__dict__
        else:
            return json.JSONEncoder.default(self, obj)

class ITCServer(object):

    def __init__(self, info, cookie_file, storage_file):
        self._info                  = info
        self.cookie_file            = cookie_file
        self.cookie_jar             = LWPCookieJar(self.cookie_file)
        self.storage_file           = storage_file
        self.applications           = []
        self._manageAppsURL         = None
        self._getApplicationListURL = None
        self._logoutURL             = None
        self._loginPageURL          = ITUNESCONNECT_MAIN_PAGE_URL

        if self.cookie_file:
            try:
                self.cookie_jar.load(self.cookie_file, ignore_discard=True)
            except IOError:
                pass

        if self.storage_file and os.path.exists(self.storage_file):
            try:
                fp = open(self.storage_file)
                appsJSON = json.load(fp)
                fp.close()
                for appJSON in appsJSON:
                    application = ITCApplication(dict=appJSON)
                    self.applications.append(application)
            except ValueError:
                pass
            except IOError:
                pass

        self.isLoggedIn = self.checkLogin()

    def cleanup(self):
        if os.path.exists(self.cookie_file):
            os.remove(self.cookie_file)

        if os.path.exists(self.storage_file):
            os.remove(self.storage_file)

        self.cookie_jar = LWPCookieJar(self.cookie_file)
        

    def logout(self):
        if not self.isLoggedIn or not self._logoutURL:
            return

        requests.get(ITUNESCONNECT_URL + self._logoutURL, cookies=self.cookie_jar)
        self.cleanup()


    def login(self):
        if self.isLoggedIn:
            # print 'Login: already logged in'
            return
        loginResponse = requests.get(ITUNESCONNECT_URL + self._loginPageURL, cookies=self.cookie_jar)
        if loginResponse.status_code == 200:
            parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
            tree = parser.parse(loginResponse.text)
            forms = tree.xpath("//form")

            if len(forms) == 0:
                raise
            
            form = forms[0]
            actionURL = form.attrib['action']
            payload = {'theAccountName': self._info.username, 'theAccountPW': self._info.password}
            mainPage = requests.post(ITUNESCONNECT_URL + actionURL, payload, cookies=self.cookie_jar)

            self.isLoggedIn = self.checkLogin(mainPageText=mainPage.text);
            if self.isLoggedIn:
                # print "Login: logged in. Saving cookies to " + self.cookie_file
                # print self.cookie_jar
                self.cookie_jar.save(self.cookie_file, ignore_discard=True)
        else:
            raise


    def checkLogin(self, mainPageText=None):
        if mainPageText == None:
            # print 'Check login: requesting main page'
            # print 'Check login: cookie jar: '
            # print self.cookie_jar
            loginResponse = requests.get(ITUNESCONNECT_URL + self._loginPageURL, cookies=self.cookie_jar)
            if loginResponse.status_code == 200:
                # print 'Check login: got main page'
                mainPageText = loginResponse.text
            else:
                print 'Check login: not logged in!'
                self.cleanup()
                return False

        parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
        tree = parser.parse(mainPageText)
        usernameInput = tree.xpath("//input[@name='theAccountName']")
        passwordInput = tree.xpath("//input[@name='theAccountPW']")

        if (len(usernameInput) == 1) and (len(passwordInput) == 1):
            print 'Check login: not logged in!'
            self.cleanup()
            return False

        print 'Check login: logged in!'
        self.parseSessionURLs(tree)
        return True


    def parseSessionURLs(self, xmlTree):
        manageAppsLink = xmlTree.xpath("//a[.='Manage Your Applications']")
        if len(manageAppsLink) == 0:
            raise

        signOutLink = xmlTree.xpath("//li[contains(@class, 'sign-out')]/a[.='Sign Out']")
        if len(signOutLink) == 0:
            raise

        self._manageAppsURL = manageAppsLink[0].attrib['href']
        self._logoutURL = signOutLink[0].attrib['href']

        print 'manage apps url: ' + self._manageAppsURL
        print 'logout url: ' + self._logoutURL


    def getApplicationsList(self):
        if self._manageAppsURL == None:
            raise 'Get applications list: not logged in'

        if not self._getApplicationListURL:
            manageAppsResponse = requests.get(ITUNESCONNECT_URL + self._manageAppsURL, cookies=self.cookie_jar)
            if manageAppsResponse.status_code != 200:
                raise

            parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False)
            tree = parser.parse(manageAppsResponse.text)
            seeAllDiv = tree.xpath("//div[@class='seeAll']")[0]
            seeAllLink = seeAllDiv.xpath("//a[starts-with(., 'See All')]")

            if len(seeAllLink) == 0:
                raise

            self._getApplicationListURL = seeAllLink[0].attrib['href']

        appsListResponse = requests.get(ITUNESCONNECT_URL + self._getApplicationListURL, cookies=self.cookie_jar)

        if appsListResponse.status_code != 200:
            raise

        appsTree = parser.parse(appsListResponse.text)
        applicationRows = appsTree.xpath("//div[@id='software-result-list']/div[@class='resultList']/table/tbody/tr[not(contains(@class, 'column-headers'))]")

        if len(applicationRows) > 0:
            self.applications = []

        for applicationRow in applicationRows:
            tds = applicationRow.xpath("td")
            nameLink = tds[0].xpath("div/p/a")
            name = nameLink[0].text.strip()
            link = nameLink[0].attrib["href"]
            applicationId = tds[4].xpath("div/p")[0].text.strip()
            application = ITCApplication(name=name, applicationId=applicationId, link=link)
            self.applications.append(application)

        if (len(self.applications) > 0) and (len(applicationRows) > 0):
            if os.path.exists(self.storage_file):
                os.remove(self.storage_file)

            fp = open(self.storage_file, "w")
            fp.write(json.dumps(self.applications, cls=ComplexEncoder))
            fp.close()

