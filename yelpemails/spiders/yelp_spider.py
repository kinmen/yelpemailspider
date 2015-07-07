import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from yelpemails.items import YelpItem

class MySpider(CrawlSpider):
    name = 'yelpemailspider'
    # start_urls = ['http://www.yelp.com/search?cflt=restaurants&find_loc=Los+Angeles%%2C+CA%%2C+USAfind_desc&start=%d' % i for i in xrange(10, 20, 10)]
    start_urls = ['http://www.yelp.com/search?cflt=restaurants&find_loc=Los+Angeles%2C+CA%2C+USAfind_desc&start=0']
    rules = (
        # Extract links matching 'category.php' (but not matching 'subsection.php')
        # and follow links from them (since no callback means follow=True by default).
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
        if email:
            item['email'] = email.strip()
            yield item
        else:
            contact = response.xpath('//body//a[re:test(., "[Cc][Oo][Nn][Tt][Aa][Cc][Tt]|[Aa][Bb][Oo][Uu][Tt]")]/@href')
            if len(contact)>0:
                contacturl = response.urljoin(contact.extract()[0])
                request = scrapy.Request(contacturl, callback = self.parse_site)
                request.meta['item'] = item
                yield request