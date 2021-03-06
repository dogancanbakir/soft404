import random
from urllib.parse import urlsplit, urlunsplit
from string import ascii_lowercase

import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError


class Spider(scrapy.Spider):
    name = 'spider'
    handle_httpstatus_list = [404]

    def __init__(self):
        self.le = LinkExtractor()
        with open('sites.txt') as f:
            self.start_urls = ['http://{}'.format(line.strip()) for line in f]

    def parse(self, response):
        if hasattr(response, 'text'):
            yield {
                'url': response.url,
                'html': response.text,
                'status': response.status,
                'headers': response.headers.to_unicode_dict(),
                'mangled_url': response.meta.get('mangled_url', False),
            }
            prob_404 = self.settings.getfloat('PROB_404')
            for link in self.le.extract_links(response):
                yield scrapy.Request(link.url, errback=self.errback_http)
                if random.random() < prob_404:  # get some 404-s
                    p = urlsplit(link.url)
                    if len(p.path.strip('/')) > 1:
                        new_path = mangle_path(p.path)
                        url = urlunsplit(
                            (p.scheme, p.netloc, new_path, p.query, p.fragment))
                        yield scrapy.Request(url, meta={'mangled_url': True},
                                             errback=self.errback_http)


    def errback_http(self, failure):
        self.logger.error(repr(failure))

        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError, TCPTimedOutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)


def mangle_path(path):
    """
    >>> random.seed(1); mangle_path('/a')
    '/sa'
    >>> random.seed(1); mangle_path('/afas')
    '/asfas'
    >>> random.seed(1); mangle_path('/afas/a/')
    '/afas/sa/'
    >>> random.seed(1); mangle_path('/afas/ab')
    '/afas/sab'
    >>> random.seed(1); mangle_path('/afas/a/ab')
    '/afas/a/sab'
    """
    lead_path, last_path = path.rstrip('/').rsplit('/', 1)
    add_idx = random.randint(0, len(last_path))
    new_last_path = ''.join([
        last_path[:add_idx],
        random.choice(ascii_lowercase),
        last_path[add_idx:]])
    new_path = '/'.join([lead_path, new_last_path])
    if path.endswith('/') and not new_path.endswith('/'):
        new_path += '/'
    return new_path
