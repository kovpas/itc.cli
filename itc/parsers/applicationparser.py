# coding=utf-8

import logging
import re
from collections import namedtuple
from datetime import datetime

from itc.parsers.baseparser import BaseParser
from itc.util import getElement
from itc.util import languages

class ITCApplicationParser(BaseParser):
    def __init__(self):
        super(ITCApplicationParser, self).__init__()

    
    def parseAppVersionsPage(self, htmlTree):
        AppVersions = namedtuple('AppVersions', ['manageInappsLink', 'customerReviewsLink', 'addVersionLink', 'versions'])

        # get 'manage in-app purchases' link
        manageInappsLink = htmlTree.xpath("//ul[@id='availableButtons']/li/a[.='Manage In-App Purchases']/@href")[0]
        customerReviewsLinkTree = htmlTree.xpath("//td[@class='value']/a[.='Customer Reviews']/@href")
        customerReviewsLink = None
        if (len(customerReviewsLinkTree) > 0):
            customerReviewsLink = customerReviewsLinkTree[0]
        logging.debug("Manage In-App purchases link: " + manageInappsLink)
        logging.debug("Customer reviews link: " + manageInappsLink)

        versionsContainer = htmlTree.xpath("//h2[.='Versions']/following-sibling::div")
        if len(versionsContainer) == 0:
            return AppVersions(manageInappsLink=manageInappsLink, customerReviewsLink=customerReviewsLink, versions={})

        versionDivs = versionsContainer[0].xpath(".//div[@class='version-container']")
        if len(versionDivs) == 0:
            return AppVersions(manageInappsLink=manageInappsLink, customerReviewsLink=customerReviewsLink, versions={})

        versions = {}
        addVersionLink = None

        for versionDiv in versionDivs:
            version = {}            
            versionString = versionDiv.xpath(".//p/label[.='Version']/../span")

            if len(versionString) == 0: # Add version
                addVersionLink = versionDiv.xpath(".//a[.='Add Version']/@href")[0]
                logging.debug('Add version link: ' + addVersionLink)
                continue
            
            versionString = versionString[0].text.strip()
            version['detailsLink'] = versionDiv.xpath(".//a[.='View Details']/@href")[0]
            version['statusString'] = ("".join([str(x) for x in versionDiv.xpath(".//span/img[starts-with(@src, '/itc/images/status-')]/../text()")])).strip()
            version['editable'] = (version['statusString'] != 'Ready for Sale')
            version['versionString'] = versionString

            logging.info("Version found: " + versionString)
            logging.debug(version)

            versions[versionString] = version

        return AppVersions(manageInappsLink=manageInappsLink, customerReviewsLink=customerReviewsLink
                            , addVersionLink=addVersionLink, versions=versions)


    def parseCreateOrEditPage(self, htmlTree, version, language=None):
        tree = htmlTree

        AppMetadata = namedtuple('AppMetadata', ['activatedLanguages', 'nonactivatedLanguages'
                                                , 'formData', 'formNames', 'submitActions'])

        localizationLightboxAction = tree.xpath("//div[@id='localizationLightbox']/@action")[0] # if no lang provided, edit default
        #localizationLightboxUpdateAction = tree.xpath("//span[@id='localizationLightboxUpdate']/@action")[0] 

        activatedLanguages    = tree.xpath('//div[@id="modules-dropdown"] \
                                    /ul/li[count(preceding-sibling::li[@class="heading"])=1]/a/text()')
        nonactivatedLanguages = tree.xpath('//div[@id="modules-dropdown"] \
                                    /ul/li[count(preceding-sibling::li[@class="heading"])=2]/a/text()')
        
        activatedLanguages = [lng.replace("(Default)", "").strip() for lng in activatedLanguages]

        logging.info('Activated languages: ' + ', '.join(activatedLanguages))
        logging.debug('Nonactivated languages: ' + ', '.join(nonactivatedLanguages))

        langs = activatedLanguages

        if language != None:
            langs = [language]

        formData = {}
        formNames = {}
        submitActions = {}
        versionString = version['versionString']

        for lang in langs:
            logging.info('Processing language: ' + lang)
            languageId = languages.appleLangIdForLanguage(lang)
            logging.debug('Apple language id: ' + languageId)

            if lang in activatedLanguages:
                logging.info('Getting metadata for ' + lang + '. Version: ' + versionString)
            elif lang in nonactivatedLanguages:
                logging.info('Add ' + lang + ' for version ' + versionString)

            editTree = self.parseTreeForURL(localizationLightboxAction + "?open=true" 
                                                    + ("&language=" + languageId if (languageId != None) else ""))
            hasWhatsNew = False

            formDataForLang = {}
            formNamesForLang = {}

            submitActionForLang = editTree.xpath("//div[@class='lcAjaxLightboxContentsWrapper']/div[@class='lcAjaxLightboxContents']/@action")[0]

            formNamesForLang['appNameName'] = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@name")[0]
            formNamesForLang['descriptionName'] = editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/@name")[0]
            whatsNewName = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/@name")

            if len(whatsNewName) > 0: # there's no what's new section for first version
                hasWhatsNew = True
                formNamesForLang['whatsNewName'] = whatsNewName[0]

            formNamesForLang['keywordsName']     = editTree.xpath("//div/label[.='Keywords']/..//input/@name")[0]
            formNamesForLang['supportURLName']   = editTree.xpath("//div/label[.='Support URL']/..//input/@name")[0]
            formNamesForLang['marketingURLName'] = editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@name")[0]
            formNamesForLang['pPolicyURLName']   = editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@name")[0]

            formDataForLang['appNameValue']     = editTree.xpath("//div[@id='appNameUpdateContainerId']//input/@value")[0]
            formDataForLang['descriptionValue'] = getElement(editTree.xpath("//div[@id='descriptionUpdateContainerId']//textarea/text()"), 0)
            whatsNewValue    = editTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/text()")

            if len(whatsNewValue) > 0 and hasWhatsNew:
                formDataForLang['whatsNewValue'] = getElement(whatsNewValue, 0)

            formDataForLang['keywordsValue']     = getElement(editTree.xpath("//div/label[.='Keywords']/..//input/@value"), 0)
            formDataForLang['supportURLValue']   = getElement(editTree.xpath("//div/label[.='Support URL']/..//input/@value"), 0)
            formDataForLang['marketingURLValue'] = getElement(editTree.xpath("//div/label[contains(., 'Marketing URL')]/..//input/@value"), 0)
            formDataForLang['pPolicyURLValue']   = getElement(editTree.xpath("//div/label[contains(., 'Privacy Policy URL')]/..//input/@value"), 0)

            logging.debug("Old values:")
            logging.debug(formDataForLang)

            iphoneUploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_35InchRetinaDisplayScreenshots']")[0]
            iphone5UploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_iPhone5']")[0]
            ipadUploadScreenshotForm = editTree.xpath("//form[@name='FileUploadForm_iPadScreenshots']")[0]

            formNamesForLang['iphoneUploadScreenshotForm'] = iphoneUploadScreenshotForm
            formNamesForLang['iphone5UploadScreenshotForm'] = iphone5UploadScreenshotForm
            formNamesForLang['ipadUploadScreenshotForm'] = ipadUploadScreenshotForm

            formData[languageId] = formDataForLang
            formNames[languageId] = formNamesForLang
            submitActions[languageId] = submitActionForLang

        metadata = AppMetadata(activatedLanguages=activatedLanguages
                             , nonactivatedLanguages=nonactivatedLanguages
                             , formData=formData
                             , formNames=formNames
                             , submitActions=submitActions)

        return metadata

    def parseAppReviewInfoForm(self, tree):
        logging.info('Updating application review information')

        AppReviewInfo = namedtuple('AppReviewInfo', ['formData', 'formNames', 'submitAction'])

        appReviewLightboxAction = tree.xpath("//div[@id='reviewInfoLightbox']/@action")[0]
        editTree = self.parseTreeForURL(appReviewLightboxAction + "?open=true")

        formNames = {}
        formData = {}

        formNames['first name']       = editTree.xpath("//div/label[.='First Name']/..//input/@name")[0]
        formNames['last name']        = editTree.xpath("//div/label[.='Last Name']/..//input/@name")[0]
        formNames['email address']    = editTree.xpath("//div/label[.='Email Address']/..//input/@name")[0]
        formNames['phone number']     = editTree.xpath("//div/label[.='Phone Number']/..//input/@name")[0]

        formNames['review notes']     = editTree.xpath("//div[@id='reviewnotes']//textarea/@name")[0]

        formNames['username']         = editTree.xpath("//div/label[.='Username']/..//input/@name")[0]
        formNames['password']         = editTree.xpath("//div/label[.='Password']/..//input/@name")[0]

        formData['first name']        = getElement(editTree.xpath("//div/label[.='First Name']/..//input/@value"), 0)
        formData['last name']         = getElement(editTree.xpath("//div/label[.='Last Name']/..//input/@value"), 0)
        formData['email address']     = getElement(editTree.xpath("//div/label[.='Email Address']/..//input/@value"), 0)
        formData['phone number']      = getElement(editTree.xpath("//div/label[.='Phone Number']/..//input/@value"), 0)
        formData['review notes']      = getElement(editTree.xpath("//div[@id='reviewnotes']//textarea/@value"), 0)
        formData['username']          = getElement(editTree.xpath("//div/label[.='Username']/..//input/@value"), 0)
        formData['password']          = getElement(editTree.xpath("//div/label[.='Password']/..//input/@value"), 0)

        submitAction = editTree.xpath("//div[@class='lcAjaxLightboxContentsWrapper']/div[@class='lcAjaxLightboxContents']/@action")[0]

        metadata = AppReviewInfo(formData=formData
                               , formNames=formNames
                               , submitAction=submitAction)
        return metadata

    def parseAddVersionPageMetadata(self, htmlTree):
        AddVersionPageInfo = namedtuple('AddVersionPageInfo', ['formNames', 'submitAction', 'saveButton'])
        formNames = {'languages': {}}

        formNames['version'] = htmlTree.xpath("//div/label[.='Version Number']/..//input/@name")[0]
        defaultLanguage = htmlTree.xpath("//div[@class='app-info-container app-landing app-version']//h2/strong/text()")[0]
        formNames['languages'][defaultLanguage] = htmlTree.xpath("//div[@id='whatsNewinthisVersionUpdateContainerId']//textarea/@name")[0]
        
        otherLanguages = htmlTree.xpath("//span[@class='metadataField metadataFieldReadonly']/textarea/../..")
        for langDiv in otherLanguages:
            lang = langDiv.xpath(".//label/text()")[0]
            taName = langDiv.xpath(".//span/textarea/@name")[0]
            formNames['languages'][lang] = taName

        submitAction = htmlTree.xpath('//form[@name="mainForm"]/@action')[0]
        saveButton = htmlTree.xpath('//input[@class="saveChangesActionButton"]/@name')[0]

        metadata = AddVersionPageInfo(formNames=formNames
                                     , submitAction=submitAction
                                     , saveButton=saveButton)

        return metadata

    def getPromocodesLink(self, htmlTree):
        link = htmlTree.xpath("//a[.='Promo Codes']")
        if len(link) == 0:
            raise('Cannot find "Promo Codes" button.')

        return link[0].attrib['href'].strip()

    def parsePromocodesPageMetadata(self, tree):
        PromoPageInfo = namedtuple('PromoPageInfo', ['amountName', 'continueButton', 'submitAction'])
        amountName = getElement(tree.xpath("//td[@class='metadata-field-code']/input/@name"), 0).strip()
        continueButton = tree.xpath("//input[@class='continueActionButton']/@name")[0].strip()
        submitAction = tree.xpath('//form[@name="mainForm"]/@action')[0]
        metadata = PromoPageInfo(amountName=amountName
                               , continueButton=continueButton
                               , submitAction=submitAction)

        return metadata

    def parsePromocodesLicenseAgreementPage(self, pageText):
        tree = self.parser.parse(pageText)
        PromoPageInfo = namedtuple('PromoPageInfo', ['agreeTickName', 'continueButton', 'submitAction'])
        agreeTickName = getElement(tree.xpath("//input[@type='checkbox']/@name"), 0).strip()
        continueButton = tree.xpath("//input[@class='continueActionButton']/@name")[0].strip()
        submitAction = tree.xpath('//form[@name="mainForm"]/@action')[0]
        metadata = PromoPageInfo(agreeTickName=agreeTickName
                               , continueButton=continueButton
                               , submitAction=submitAction)

        return metadata

    def getDownloadCodesLink(self, pageText):
        tree = self.parser.parse(pageText)
        link = tree.xpath("//img[@alt='Download Codes']/../@href")
        if len(link) == 0:
            raise('Cannot find "Download Codes" button.')

        return link[0].strip()

    def getReviewsPageMetadata(self, tree):
        ReviewsPageInfo = namedtuple('ReviewsPageInfo', ['countries', 'countriesSelectName', 'countryFormSubmitAction', 'allVersions', 'currentVersion', 'allReviews'])
        countriesSelectName = tree.xpath('//select/@name')[0].strip()
        countriesSelect = tree.xpath('//select/option')
        countries = {}
        for countryOption in countriesSelect:
            countries[countryOption.text.strip()] = countryOption.attrib['value']

        countryFormSubmitAction = tree.xpath('//form/@action')[0]
        allVersionsLink = tree.xpath('//div[@class="button-container"]//a')[0].attrib['href'].strip()
        currentVersionLink = tree.xpath('//div[@class="button-container"]//a')[1].attrib['href'].strip()
        allReviewsLink = tree.xpath('//span[@class="paginatorBatchSizeList"]//a[.="All"]')[0].attrib['href'].strip()

        metadata = ReviewsPageInfo(countries=countries
                                 , countriesSelectName=countriesSelectName
                                 , allVersions=allVersionsLink
                                 , currentVersion=currentVersionLink
                                 , allReviews=allReviewsLink
                                 , countryFormSubmitAction=countryFormSubmitAction)

        return metadata

    def parseReviews(self, pageText, minDate=None, maxDate=None):
        tree = self.parser.parse(pageText)
        reviewDivs = tree.xpath('//div[@class="reviews-container"]')
        
        if len(reviewDivs) == 0:
            return None

        reviews = []
        for reviewDiv in reviewDivs:
            review = {} 
            reviewerString = getElement(reviewDiv.xpath('./p[@class="reviewer"]'), 0).text.strip()
            regexp = re.compile('by\s+(.*)-\sVersion(.*)-\s*(.*)', re.DOTALL)
            m = regexp.search(reviewerString)
            review['reviewer'] = m.group(1).strip()
            review['version'] = m.group(2).strip()
            review['date'] = m.group(3).strip()
            reviewDate = datetime.strptime(review['date'], '%b %d, %Y')
            if minDate != None and reviewDate < minDate:
                break
            if maxDate != None and reviewDate > maxDate:
                continue

            title = getElement(reviewDiv.xpath('./p[@class="reviewer-title"]'), 0).text.strip()
            review['title'] = title.replace(u'★', '').strip()
            review['mark'] = len(title.replace(review['title'], '').strip())

            review['text'] = getElement(reviewDiv.xpath('./p[@class="review-text"]'), 0).text.strip()
            reviews.append(review)

        return reviews