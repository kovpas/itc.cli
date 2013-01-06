import logging 
from collections import namedtuple

from itc.parsers.baseparser import BaseParser
from itc.util import languages

class ITCInappParser(BaseParser):
    def __init__(self):
        super(ITCInappParser, self).__init__()


    def metadataForInappPurchase(self, htmlTree):
        InappMetadata = namedtuple('InappMetadata', ['refname', 'cleared', 'languages', 'textid', 'numericid', 'price_tier', 'reviewnotes', 'hosted'])

        inappReferenceName = htmlTree.xpath('//span[@id="iapReferenceNameUpdateContainer"]//span/text()')[0].strip()
        textId = htmlTree.xpath('//div[@id="productIdText"]//span/text()')[0].strip()
        numericId = htmlTree.xpath('//label[.="Apple ID: "]/following-sibling::span/text()')[0].strip()
        hostedContent = len(htmlTree.xpath('//div[contains(@class,"hosted-content")]/following-sibling::p')) > 0
        reviewNotes = htmlTree.xpath('//div[@class="hosted-review-notes"]//span/text()')[0].strip()

        clearedForSaleText = htmlTree.xpath('//div[contains(@class,"cleared-for-sale")]//span/text()')[0]
        clearedForSale = False
        if clearedForSaleText == 'Yes':
            clearedForSale = True

        inapptype = htmlTree.xpath('//div[@class="status-label"]//span/text()')[0].strip()
        priceTier = None

        if inapptype != "Free Subscription":
            priceTier = htmlTree.xpath('//tr[@id="interval-row-0"]//a/text()')[0].strip().split(' ')
            priceTier = int(priceTier[-1])

        idAddon = "autoRenewableL" if (inapptype == "Free Subscription") else "l"
        languagesSpan = htmlTree.xpath('//span[@id="0' + idAddon + 'ocalizationListListRefreshContainerId"]')[0]
        activatedLanguages = languagesSpan.xpath('.//li[starts-with(@id, "0' + idAddon + 'ocalizationListRow")]/div[starts-with(@class, "ajaxListRowDiv")]/@itemid')
        activatedLangsIds = [languages.langCodeForLanguage(lang) for lang in activatedLanguages]
        languageAction = htmlTree.xpath('//div[@id="0' + idAddon + 'ocalizationListLightbox"]/@action')[0]

        # logging.info('Activated languages for inapp ' + self.numericId + ': ' + ', '.join(activatedLanguages))
        logging.debug('Activated languages ids: ' + ', '.join(activatedLangsIds))
        metadataLanguages = {}

        for langId in activatedLangsIds:
            metadataLanguages[langId] = {}
            languageParamStr = "&itemID=" + languages.appleLangIdForLanguage(langId)
            localizationTree = self.parseTreeForURL(languageAction + "?open=true" + languageParamStr)
            metadataLanguages[langId]['name'] = localizationTree.xpath('//div[@id="proposedDisplayName"]//input/@value')[0]
            metadataLanguages[langId]['description'] = localizationTree.xpath('//div[@id="proposedDescription"]//textarea/text()')[0].strip()
    
            localizedPublicationName = localizationTree.xpath('//div[@id="proposedPublicationName"]//input/@value')
            if len(localizedPublicationName) > 0:
                metadataLanguages[langId]['publication name'] = localizedPublicationName[0]

        return InappMetadata(refname=inappReferenceName
                            , cleared=clearedForSale
                            , languages=metadataLanguages
                            , price_tier=priceTier
                            , textid=textId
                            , numericid=int(numericId)
                            , hosted=hostedContent
                            , reviewnotes=reviewNotes)

