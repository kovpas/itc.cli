import logging
from collections import namedtuple

from itc.parsers.baseparser import BaseParser

ApplicationData = namedtuple('SessionURLs', ['name', 'applicationId', 'link'])

class ITCServerParser(BaseParser):
    def __init__(self):
        self._manageAppsURL         = None
        self._createAppURL          = None
        self._getApplicationListURL = None
        self._logoutURL             = None
        super(ITCServerParser, self).__init__()


    def isLoggedIn(self, htmlTree):
        usernameInput = htmlTree.xpath("//input[@name='theAccountName']")
        passwordInput = htmlTree.xpath("//input[@name='theAccountPW']")

        if not ((len(usernameInput) == 1) and (len(passwordInput) == 1)):
            self.parseSessionURLs(htmlTree)
            return True

        return False


    def parseSessionURLs(self, htmlTree):
        manageAppsLink = htmlTree.xpath("//a[.='Manage Your Apps']")
        if len(manageAppsLink) == 0:
            raise

        signOutLink = htmlTree.xpath("//li[contains(@class, 'sign-out')]/a[.='Sign Out']")
        if len(signOutLink) == 0:
            raise

        self._manageAppsURL = manageAppsLink[0].attrib['href']
        self._logoutURL = signOutLink[0].attrib['href']

        logging.debug('manage apps url: ' + self._manageAppsURL)
        logging.debug('logout url: ' + self._logoutURL)


    def __getInternalURLs(self):
        tree = self.parseTreeForURL(self._manageAppsURL)

        seeAllDiv = tree.xpath("//div[@class='seeAll']")[0]
        seeAllLink = seeAllDiv.xpath(".//a[starts-with(., 'See All')]")

        if len(seeAllLink) == 0:
            raise

        self._getApplicationListURL = seeAllLink[0].attrib['href']

        createAppLink = tree.xpath("//span[@class='upload-app-button']/a")

        if len(createAppLink) == 0:
            raise

        self._createAppURL = createAppLink[0].attrib['href']


    def getApplicationsData(self):
        if self._manageAppsURL == None:
            raise Exception('Get applications list: not logged in')

        # support multiple pages

        if not self._getApplicationListURL:
            self.__getInternalURLs()

        appsTree = self.parseTreeForURL(self._getApplicationListURL)
        applicationRows = appsTree.xpath("//div[@id='software-result-list'] \
                            /div[@class='resultList']/table/tbody/tr[not(contains(@class, 'column-headers'))]")

        result = []
        for applicationRow in applicationRows:
            tds = applicationRow.xpath("td")
            nameLink = tds[0].xpath(".//a")
            name = nameLink[0].text.strip()
            link = nameLink[0].attrib["href"]
            applicationId = int(tds[4].xpath(".//p")[0].text.strip())

            result.append(ApplicationData(name=name, link=link, applicationId=applicationId))

        return result

    def parseFirstAppCreatePageForm(self):
        if self._manageAppsURL == None:
            raise Exception('Create application: not logged in')

        if not self._createAppURL:
            self.__getInternalURLs()

        formNames = {}
        AppMetadata = namedtuple('AppMetadata', ['formNames', 'submitAction', 'languageIds', 'bundleIds'])

        createAppTree = self.parseTreeForURL(self._createAppURL)
        createAppForm = createAppTree.xpath("//form[@id='mainForm']")[0]
        submitAction = createAppForm.attrib['action']

        formNames['default language'] = createAppForm.xpath("//select[@id='default-language-popup']/@name")[0]
        formNames['app name']         = createAppForm.xpath("//div/label[.='App Name']/..//input/@name")[0]
        formNames['sku number']       = createAppForm.xpath("//div/label[.='SKU Number']/..//input/@name")[0]
        formNames['bundle id']        = createAppForm.xpath("//select[@id='primary-popup']/@name")[0]
        formNames['bundle id suffix'] = createAppForm.xpath("//div/label[.='Bundle ID Suffix']/..//input/@name")[0]

        languageIds = {}
        languageIdOptions = createAppForm.xpath("//select[@id='default-language-popup']/option")
        for langIdOption in languageIdOptions:
            languageIds[langIdOption.text.strip()] = langIdOption.attrib['value']

        bundleIds = {}
        bundleIdOptions = createAppForm.xpath("//select[@id='primary-popup']/option")
        for bundIdOption in bundleIdOptions:
            bundleIds[bundIdOption.text.strip()] = bundIdOption.attrib['value']

        metadata = AppMetadata(formNames=formNames
                             , submitAction=submitAction
                             , languageIds=languageIds
                             , bundleIds=bundleIds)

        return metadata
