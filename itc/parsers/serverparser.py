import logging
from collections import namedtuple

from itc.parsers.baseparser import BaseParser

ApplicationData = namedtuple('SessionURLs', ['name', 'applicationId', 'link'])

class ITCServerParser(BaseParser):
    def __init__(self):
        self._manageAppsURL         = None
        self._getApplicationListURL = None
        self._logoutURL             = None
        super(ITCServerParser, self).__init__()


    def isLoggedIn(self, htmlTree):
        usernameInput = htmlTree.xpath("//input[@name='theAccountName']")
        passwordInput = htmlTree.xpath("//input[@name='theAccountPW']")

        if not ((len(usernameInput) == 1) and (len(passwordInput) == 1)):
            try:
                self.parseSessionURLs(htmlTree)
            except:
                return False
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


    def __getApplicationsListURL(self):
        tree = self.parseTreeForURL(self._manageAppsURL)

        seeAllDiv = tree.xpath("//div[@class='seeAll']")[0]
        seeAllLink = seeAllDiv.xpath(".//a[starts-with(., 'See All')]")

        if len(seeAllLink) == 0:
            raise

        self._getApplicationListURL = seeAllLink[0].attrib['href']


    def getApplicationsData(self):
        if self._manageAppsURL == None:
            raise Exception('Get applications list: not logged in')

        # support multiple pages

        if not self._getApplicationListURL:
            self.__getApplicationsListURL()

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

    def loginContinueButton(self, htmlTree):
        continueButtonLink = htmlTree.xpath("//img[@class='customActionButton']/..")
        if len(continueButtonLink) == 0:
            return None

        return continueButtonLink[0].attrib['href']
