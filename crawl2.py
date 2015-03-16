# -*- coding: utf-8 -*-
__author__ = 'Excelle'

import sys, re, os
import urllib2
import time
import string
from multiprocessing import Pool, Queue
from HTMLParser import HTMLParser
from urlparse import urljoin, urlparse
from logging import exception

_RE_VOID_LINK = re.compile(r'^#*$')
_RE_SCRIPT_LINK = re.compile(r'^javascript*$')
_LOGFILE = 'cralwer.log'

url_list = Queue()
base_url = ''
base_dir = ''
debug_mode = True


def addFileName(url):
    list = re.split('/', url)
    if not list[-1]:
        return url + 'index.html'
    return url


def getDirectory(url):
    list = re.split('/', url)
    list.pop(-1)
    return string.join(list, '/')


def log(info):
    if debug_mode:
        print(time.strftime('%Y-%m-%d %H:%M:%S') + ' :' + info)
    with open(_LOGFILE, 'a') as f:
        f.writelines(time.strftime('%Y-%m-%d %H:%M:%S') + ' :' + info)


class MyHTMLParser(HTMLParser):
    '''
    HTML Parser
    ===============
    This is to read all links consisting in the given HTML code.
    Such tags will be parsed and links will be put into the queue:
    1.  <script src="..."></script>
    2.  <a href="..."></a>
    3.  <img src="..." />
    4.  <link rel="..." />
    '''

    def handle_starttag(self, tag, attrs):
        attr = dict()
        attr['src'] = ''
        attr['href'] = ''

        for key, value in attrs:
            attr[key] = value
        if tag == 'script' and attr['src']:
            if not os.path.exists('./' + base_dir + addFileName(attr['src'])):
                url_list.put(attr['src'])
                log('Put %s into queue' % attr['src'])
        elif tag == 'a' and attr['href']:
            if not os.path.exists('./' + base_dir + addFileName(attr['href'])):
                url_list.put(attr['href'])
                log('Put %s into queue' % attr['href'])

    def handle_startendtag(self, tag, attrs):
        attr = dict()
        attr['src'] = ''
        attr['rel'] = ''
        for key, value in attrs:
            attr[key] = value
        if tag == 'img' and attr['src']:
            if not os.path.exists('./' + base_dir + addFileName(attr['src'])):
                url_list.put(attr['src'])
                log('Put %s into queue' % attr['src'])

        elif tag == 'link' and attr['rel']:
            if not os.path.exists('./' + base_dir + addFileName(attr['rel'])):
                url_list.put(attr['rel'])
                log('Put %s into queue' % attr['rel'])

'''
    UA-safari:
    User-Agent	Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5)
                AppleWebKit/600.3.18 (KHTML, like Gecko) Version/7.1.3 Safari/537.85.12
'''


def worker():
    log('Run process: %s' % os.getpid())
    while not url_list.empty():
        worker_once()


def worker_once():
    try:
        url = url_list.get()
        url = urljoin(base_url, url)
        parts = urlparse(url)
        if os.path.exists('./' + base_dir + addFileName(parts.path)):
            return

        if parts.netloc != base_dir:
            os.system('nohup python ' + sys.argv[0] + ' http://' + parts.netloc + ' > log'
            + str(time.time()) + '.txt' + ' &')
            return

        reqobj = urllib2.Request(url)
        reqobj.add_header('Host', parts.netloc)
        reqobj.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5)'
                                        ' AppleWebKit/600.3.18 (KHTML, like Gecko) Version/7.1.3 Safari/537.85.12')
        reqobj.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        reqobj.add_header('Accept-Language', 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3')
        log('Crawling: %s' % url)
        url_opener = urllib2.urlopen(reqobj)
        data = url_opener.read()
        htmlparse = MyHTMLParser()
        htmlparse.feed(data)

        try:
            os.makedirs(getDirectory('./' + base_dir + parts.path))
        except OSError:
            pass

        with open('./' + base_dir + addFileName(parts.path), 'w+') as fp:
            fp.write(data)
        log('Write file into: %s' % parts.path)
    except Exception, ex:
        log(ex.message)
        exception(ex)

if __name__ == '__main__':
    pars = sys.argv
    if pars.__len__() > 1:
        base_url = pars[1]
        url_list.put(base_url)
        base_dir = urlparse(base_url).netloc
        log('Dedicated website: %s' % base_url)
        log('Launched parent process: %s' % os.getpid())
        log('Doing the first iteration...')
        worker()
        p = Pool()
        for i in range(4):
            p.apply_async(worker, args=())
        print('Doing all processes...')
        p.close()
        p.join()
        log('All process done.')
    else:
        print('An argument about the website URL required.')