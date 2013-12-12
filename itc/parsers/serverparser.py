import logging
from collections import namedtuple

from itc.parsers.baseparser import BaseParser
import pprint

ApplicationData = namedtuple('SessionURLs', ['name', 'applicationId', 'link'])

class ITCServerParser(BaseParser):
    def __init__(self):
        self._manageAppsURL         = None
        self._createAppURL          = None
        self._getApplicationListURL = None
        self._logoutURL             = None
        super(ITCServerParser, self).__init__()


    def isLoggedIn(self, htmlTree):
        usernameInput = htmlTree.xpath("//input[@id='accountname']")
        passwordInput = htmlTree.xpath("//input[@id='accountpassword']")

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

    def getApplicationDataById(self, _applicationId):
        if self._manageAppsURL == None:
            raise Exception('Get applications list: not logged in')

        if not self._getApplicationListURL:
            self.__getInternalURLs()

        result = None
        nextLink = self._getApplicationListURL;
        while (nextLink != None):
            appsTree = self.parseTreeForURL(nextLink)
            nextLinkDiv = appsTree.xpath("//td[@class='previous']")
            if len(nextLinkDiv) > 0:
                nextLink = nextLinkDiv[0].xpath(".//a[contains(., ' Previous')]/@href")[0]
            else:
                nextLink = None

        nextLink = self._getApplicationListURL;
        while (nextLink != None) and (result == None):
            appsTree = self.parseTreeForURL(nextLink)
            applicationRows = appsTree.xpath("//div[@id='software-result-list'] \
                            /div[@class='resultList']/table/tbody/tr[not(contains(@class, 'column-headers'))]")
            for applicationRow in applicationRows:
                tds = applicationRow.xpath("td")
                applicationId = int(tds[4].xpath(".//p")[0].text.strip())
                if (applicationId == _applicationId):
                    nameLink = tds[0].xpath(".//a")
                    name = nameLink[0].text.strip()
                    link = nameLink[0].attrib["href"]
                    result = ApplicationData(name=name, link=link, applicationId=applicationId)
                    break;

            nextLinkDiv = appsTree.xpath("//td[@class='next']")
            if len(nextLinkDiv) > 0:
                nextLink = nextLinkDiv[0].xpath(".//a[starts-with(., ' Next')]/@href")[0]
            else:
                nextLink = None

        return result

    def getApplicationsData(self):
        if self._manageAppsURL == None:
            raise Exception('Get applications list: not logged in')

        if not self._getApplicationListURL:
            self.__getInternalURLs()

        result = []
        nextLink = self._getApplicationListURL;
        while nextLink!=None:
            appsTree = self.parseTreeForURL(nextLink)
            applicationRows = appsTree.xpath("//div[@id='software-result-list'] \
                            /div[@class='resultList']/table/tbody/tr[not(contains(@class, 'column-headers'))]")
            for applicationRow in applicationRows:
                tds = applicationRow.xpath("td")
                nameLink = tds[0].xpath(".//a")
                name = nameLink[0].text.strip()
                link = nameLink[0].attrib["href"]
                applicationId = int(tds[4].xpath(".//p")[0].text.strip())
                result.append(ApplicationData(name=name, link=link, applicationId=applicationId))

            nextLinkDiv = appsTree.xpath("//td[@class='next']")
            if len(nextLinkDiv) > 0:
                nextLink = nextLinkDiv[0].xpath(".//a[starts-with(., ' Next')]/@href")[0]
            else:
                nextLink = None

        return result

    def parseFirstAppCreatePageForm(self):
        if self._manageAppsURL == None:
            raise Exception('Create application: not logged in')

        if not self._createAppURL:
            self.__getInternalURLs()

        formNames = {}
        AppMetadata = namedtuple('AppMetadata', ['formNames', 'submitAction', 'languageIds', 'bundleIds', 'selectedLanguageId'])

        createAppTree = self.parseTreeForURL(self._createAppURL)
        createAppForm = createAppTree.xpath("//form[@id='mainForm']")[0]
        submitAction = createAppForm.attrib['action']

        formNames['default language'] = createAppForm.xpath("//select[@id='default-language-popup']/@name")[0]
        formNames['app name']         = createAppForm.xpath("//div/label[.='App Name']/..//input/@name")[0]
        formNames['sku number']       = createAppForm.xpath("//div/label[.='SKU Number']/..//input/@name")[0]
        formNames['bundle id']        = createAppForm.xpath("//select[@id='primary-popup']/@name")[0]
        formNames['bundle id suffix'] = createAppForm.xpath("//div/label[.='Bundle ID Suffix']/..//input/@name")[0]
        formNames['continue action']  = createAppForm.xpath("//input[@class='continueActionButton']/@name")[0]

        languageIds = {}
        languageIdOptions = createAppForm.xpath("//select[@id='default-language-popup']/option")
        selectedLanguageId = '-1'
        for langIdOption in languageIdOptions:
            if langIdOption.text.strip() != 'Select':
                languageIds[langIdOption.text.strip()] = langIdOption.attrib['value']
                if 'selected' in langIdOption.attrib:
                    selectedLanguageId = langIdOption.attrib['value']


        bundleIds = {}
        bundleIdOptions = createAppForm.xpath("//select[@id='primary-popup']/option")
        for bundIdOption in bundleIdOptions:
            if bundIdOption.text.strip() != 'Select':
                bundleIds[bundIdOption.text.strip()] = bundIdOption.attrib['value']

        metadata = AppMetadata(formNames=formNames
                             , submitAction=submitAction
                             , languageIds=languageIds
                             , bundleIds=bundleIds
                             , selectedLanguageId=selectedLanguageId)

        return metadata

    def parseSecondAppCreatePageForm(self, createAppTree):
        formNames = {}
        AppMetadata = namedtuple('AppMetadata', ['formNames', 'submitAction', 'countries'])

        createAppForm = createAppTree.xpath("//form[@id='mainForm']")[0]
        submitAction = createAppForm.attrib['action']

        formNames['date day']   = createAppForm.xpath("//span[@class='date-select-day']/select/@name")[0]
        formNames['date month'] = createAppForm.xpath("//span[@class='date-select-month']/select/@name")[0]
        formNames['date year']  = createAppForm.xpath("//span[@class='date-select-year']/select/@name")[0]
        formNames['price tier'] = createAppForm.xpath("//span[@id='pricingTierUpdateContainer']/select/@name")[0]
        formNames['discount']   = createAppForm.xpath("//input[@id='education-checkbox']/@name")[0]
        formNames['continue action']  = createAppForm.xpath("//input[@class='continueActionButton']/@name")[0]

        countries = {}
        countryInputs = createAppForm.xpath("//table[@id='countries-list']//input[@class='country-checkbox']/../..")
        for countryInput in countryInputs:
            countries[countryInput.xpath("td")[0].text.strip()] = countryInput.xpath("td/input[@class='country-checkbox']")[0].attrib['value']

        metadata = AppMetadata(formNames=formNames
                             , submitAction=submitAction
                             , countries=countries)

        return metadata

    def parseThirdAppCreatePageForm(self, htmlTree, fetchSubcategories=False):
        formNames = {}
        AppMetadata = namedtuple('AppMetadata', ['formNames', 'submitAction', 'categories', 'subcategories', 'appRatings', 'eulaCountries'])
        
        versionForm = htmlTree.xpath("//form[@id='versionInitForm']")[0]
        submitAction = versionForm.attrib['action']
        formNames['version number'] = versionForm.xpath("//div[@id='versionNumberTooltipId']/../input/@name")[0]
        formNames['copyright'] = versionForm.xpath("//div[@id='copyrightTooltipId']/../input/@name")[0]
        formNames['primary category'] = versionForm.xpath("//select[@id='version-primary-popup']/@name")[0]
        formNames['primary subcategory 1'] = versionForm.xpath("//select[@id='primary-first-popup']/@name")[0]
        formNames['primary subcategory 2'] = versionForm.xpath("//select[@id='primary-second-popup']/@name")[0]
        formNames['secondary category'] = versionForm.xpath("//select[@id='version-secondary-popup']/@name")[0]
        formNames['secondary subcategory 1'] = versionForm.xpath("//select[@id='secondary-first-popup']/@name")[0]
        formNames['secondary subcategory 2'] = versionForm.xpath("//select[@id='secondary-second-popup']/@name")[0]
        categories = {}
        subcategories = None

        categoryOptions = versionForm.xpath("//select[@id='version-primary-popup']/option")
        for categoryOption in categoryOptions:
            if categoryOption.text.strip() != 'Select':
                categories[categoryOption.text.strip()] = categoryOption.attrib['value']

        if fetchSubcategories:
            categoryId = categories[fetchSubcategories];
            subcategoriesURL = htmlTree.xpath('//span[@id="primaryCategoryContainer"]/@action')[0]
            formData = {'viaLCAjaxContainer':'true'}
            formData[formNames['primary category']] = categoryId
            formData[formNames['primary subcategory 1']] = 'WONoSelectionString'
            formData[formNames['primary subcategory 2']] = 'WONoSelectionString'

            subcategoriesTree = self.parseTreeForURL(subcategoriesURL, method="POST", payload=formData)
            subcategoryOptions = subcategoriesTree.xpath("//select[@id='primary-first-popup']/option")
            subcategories = {}
            for categoryOption in subcategoryOptions:
                if categoryOption.text.strip() != 'Select':
                    subcategories[categoryOption.text.strip()] = categoryOption.attrib['value']

        appRatings = []
        appRatingTable = versionForm.xpath('//tr[@id="game-ratings"]/td/table/tbody/tr')

        for ratingTr in appRatingTable:
            inputs = ratingTr.xpath('.//input')
            if len(inputs) != 3:
                continue
            appRating = {'name': inputs[0].attrib['name'], 'ratings': []}
            for inpt in inputs:
                appRating['ratings'].append(inpt.attrib['value'])
            appRatings.append(appRating)

        formNames['description'] = versionForm.xpath("//div[@id='descriptionUpdateContainerId']/div/span/textarea/@name")[0]
        formNames['keywords'] = versionForm.xpath("//div[@id='keywordsTooltipId']/../input/@name")[0]
        formNames['support url'] = versionForm.xpath("//div[@id='supportURLTooltipId']/../input/@name")[0]
        formNames['marketing url'] = versionForm.xpath("//div[@id='marketingURLOptionalTooltipId']/../input/@name")[0]
        formNames['privacy policy url'] = versionForm.xpath("//div[@id='privacyPolicyURLTooltipId']/../input/@name")[0]

        formNames['first name'] = versionForm.xpath("//div/label[.='First Name']/../span/input/@name")[0]
        formNames['last name'] = versionForm.xpath("//div/label[.='Last Name']/../span/input/@name")[0]
        formNames['email address'] = versionForm.xpath("//div/label[.='Email Address']/../span/input/@name")[0]
        formNames['phone number'] = versionForm.xpath("//div/label[.='Phone Number']/../span/input/@name")[0]
        formNames['review notes'] = versionForm.xpath("//div[@id='reviewnotes']/div/span/textarea/@name")[0]
        formNames['username'] = versionForm.xpath("//div/label[.='Username']/../span/input/@name")[0]
        formNames['password'] = versionForm.xpath("//div/label[.='Password']/../span/input/@name")[0]

        formNames['eula text'] = versionForm.xpath("//textarea[@id='eula-text']/@name")[0]
        eulaCountries = {}
        countryDivs = versionForm.xpath("//div[@class='country group']")
        for countryDiv in countryDivs:
            name = countryDiv.xpath("./div[@class='country-name']")[0].text.strip()
            eulaCountries[name] = countryDiv.xpath("./div[@class='country-check-box']/input[@class='country-checkbox']")[0].attrib['value']

        iconUploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_largeAppIcon']")[0]
        iphoneUploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_35InchRetinaDisplayScreenshots']")[0]
        iphone5UploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_iPhone5']")[0]
        ipadUploadScreenshotForm = versionForm.xpath("//form[@name='FileUploadForm_iPadScreenshots']")[0]
        tfUploadForm = versionForm.xpath("//form[@name='FileUploadForm_tfUploader']")[0]

        formNames['iconUploadScreenshotForm'] = iconUploadScreenshotForm
        formNames['iphoneUploadScreenshotForm'] = iphoneUploadScreenshotForm
        formNames['iphone5UploadScreenshotForm'] = iphone5UploadScreenshotForm
        formNames['ipadUploadScreenshotForm'] = ipadUploadScreenshotForm
        formNames['tfUploadForm'] = tfUploadForm

        metadata = AppMetadata(formNames=formNames
                             , submitAction=submitAction
                             , categories=categories
                             , subcategories=subcategories
                             , eulaCountries=eulaCountries
                             , appRatings=appRatings)

        return metadata

    def checkPageForErrors(self, htmlTree):
        errors = htmlTree.xpath("//div[@id='LCPurpleSoftwarePageWrapperErrorMessage']/div/ul/li/span/text()")

        return errors

    def loginContinueButton(self, htmlTree):
        continueButtonLink = htmlTree.xpath("//img[@class='customActionButton']/..")
        if len(continueButtonLink) == 0:
            return None

        return continueButtonLink[0].attrib['href']
