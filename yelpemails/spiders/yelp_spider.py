import scrapy
import json
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from yelpemails.items import YelpItem

class MySpider(CrawlSpider):
    name = 'yelpemailspider'
    FBaccesstoken = 'fillintokenhere'
    # start_urls = ['http://www.yelp.com/search?cflt=restaurants&find_loc=Los+Angeles%%2C+CA%%2C+USAfind_desc&start=%d' % i for i in xrange(10, 20, 10)]
    start_urls = ['http://www.yelp.com/search?cflt=restaurants&find_loc=Los+Angeles%2C+CA%2C+USAfind_desc&start=0']
    rules = (
        # Extract yelp link for each business listing
        Rule(LinkExtractor(restrict_css=('.indexed-biz-name .biz-name', )), callback = 'parse_yelp'),

        # Extract links matching 'item.php' and parse them with the spider's method parse_yelp
        # Rule(LinkExtractor(allow=('item\.php', )), callback='parse_yelp'),

        Rule(LinkExtractor(restrict_xpaths=('//a[@class = "page-option prev-next next"]', )))
    )

    def parse_yelp(self, response):
        self.logger.info('Hi, this is an item page! %s', response.url)
        biz = response.xpath('//div[@class = "biz-website"]')
        websiteurl = biz.xpath('a/text()').extract()
        if len(websiteurl)>0:
            name = response.xpath('//h1[contains(@class,"biz-page-title")]/text()').extract()
            item = YelpItem()
            item['name'] = name[0].strip()
            item['website'] = websiteurl[0].strip()
            # item['id'] = response.xpath('//td[@id="item_id"]/text()').re(r'ID: (\d+)')
            # item['name'] = response.xpath('//td[@id="item_name"]/text()').extract()
            # item['description'] = response.xpath('//td[@id="item_description"]/text()').extract()
            # href = biz.xpath('a/@href')
            # url = response.urljoin(href.extract()[0])
            request = scrapy.Request('http://'+ websiteurl[0], callback = self.parse_site)
            request.meta['item'] = item
            yield request

    def parse_site(self, response):
        item = response.meta['item']
        email = response.xpath('//body//text()').re_first(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        facebook = response.xpath('//a[contains(@href, "facebook.com")]/@href')
        if facebook:
            item['facebook'] = facebook.extract()[0]
        if email:
            item['email'] = email.strip()
            yield item
        else:
            contact = response.xpath('//body//a[re:test(., "[Cc][Oo][Nn][Tt][Aa][Cc][Tt]|[Aa][Bb][Oo][Uu][Tt]")]/@href')
            if len(contact)>0:
                contacturl = response.urljoin(contact.extract()[0])
                request = scrapy.Request(contacturl, callback = self.parse_contact)
                request.meta['item'] = item
                yield request
            else:
                if facebook:
                    facebookurl = item['facebook']
                    fbgeturl = 'https://graph.facebook.com/v2.4/'+facebookurl+'?access_token='+self.FBaccesstoken+'&fields=emails'
                    request = scrapy.Request(fbgeturl, callback = self.parse_facebook)
                    request.meta['item'] = item
                    yield request

    def parse_contact(self,response):
        item = response.meta['item']
        email = response.xpath('//body//text()').re_first(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        if email:
            item['email'] = email.strip()
            yield item
        else:
            facebookurl = ''
            if 'facebook' in item:
                facebookurl = item['facebook']
            else:
                facebook = response.xpath('//a[contains(@href, "www.facebook.com")]/@href')
                if len(facebook) > 0:
                    facebookurl = facebook.extract()[0]

            if facebookurl:
                fbgeturl = 'https://graph.facebook.com/v2.4/'+facebookurl+'?access_token='+self.FBaccesstoken+'&fields=emails'
                request = scrapy.Request(fbgeturl, callback = self.parse_facebook)
                request.meta['item'] = item
                yield request

    def parse_facebook(self,response):
        item = response.meta['item']
        jsonresponse = json.loads(response.body)
        if 'emails' in jsonresponse:
            item['email'] = json.loads(response.body)['emails'][0]
            yield item