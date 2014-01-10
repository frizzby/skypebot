import random
import urllib2
import csv
import urlparse
import time
from itertools import ifilter
import string

import pytumblr


class TumblrRestClient(pytumblr.TumblrRestClient):
    def send_api_request(self, method, url, params={}, valid_parameters=[], needs_api_key=False):
        """
        Sends the url with parameters to the requested url, validating them
        to make sure that they are what we expect to have passed to us

        :param method: a string, the request method you want to make
        :param params: a dict, the parameters used for the API request
        :param valid_parameters: a list, the list of valid parameters
        :param needs_api_key: a boolean, whether or not your request needs an api key injected

        :returns: a dict parsed from the JSON response
        """
        if needs_api_key:
            params.update({'api_key': self.request.consumer.key})
            valid_parameters.append('api_key')

        files = []
        if 'data' in params:
            files = []
            if not isinstance(params['data'], list):
                params['data'] = [params['data']]
            for idx, data in enumerate(params['data']):
                try:
                    img = urllib2.urlopen(data).read()
                    if not img:
                        raise RuntimeError("Empty data")
                    name = ''.join(random.choice(string.ascii_uppercase) for x in range(10))
                    print "<===", data
                    files.append(('data[' + str(idx) + ']', "%s.%s" % (name, str(data.split('.')[-1])), img))
                except (urllib2.HTTPError, RuntimeError) as e:
                    print "Unable to fetch photo: %s (%s)" % (e, data)

            del params['data']

        pytumblr.validate_params(valid_parameters, params)
        if not files:
            raise RuntimeError("No photos to post")
        if method == "get":
            return self.request.get(url, params)
        else:
            return self.request.post(url, params, files)


client = TumblrRestClient(
)

BLOG_NAME = ''
OUTPUT_FILENAME = 'urls.csv'
LATEST_FILE = 'latest.txt'
TAGS = ['girls', 'boobs']



def follow(thefile):
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(10)
            continue
        yield line


try:
    with open(LATEST_FILE, 'r') as f:
        latest = f.read().strip()
except IOError:
    latest = None



logfile = open(OUTPUT_FILENAME, 'r')

while latest and (latest != logfile.readline().strip()):
    pass
if latest:
    logfile.readline()


def url_norm(url):
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    return urlparse.urlunparse((scheme, netloc.encode("idna"), path, params, query, fragment))

post_size = random.randint(1, 10)
data = []
tags = []
for item in csv.reader(ifilter(None, follow(logfile))):
    data.append(url_norm(item[2].decode('utf-8')))
    tags.append(item[1])
    if len(data) == post_size:
        print "Posting %s photos" % post_size
        response = client.create_photo(BLOG_NAME, data=data, tags=TAGS + tags)
        print response
        if "id" not in response or ('meta' in response and (response['meta']['status'] != 201)):
            raise Exception("Bad response: %s" % response)
        data = []
        tags = []
        post_size = random.randint(1, 10)
        with open(LATEST_FILE, 'w') as f:
            csv.writer(f).writerow(item)

        wait = random.randint(45, 60*60)
        print "=== Waiting %s sec. === " % wait
        time.sleep(wait)

