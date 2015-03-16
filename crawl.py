# -*- coding: utf-8 -*-
__author__ = 'Excelle'

'''
    Net Crawler v0.1.1
    Usage: python crawl.py <url>
    This program will crawl your assigned website and download all file on it.
    To have it run on the background, please use command:
    $ nohup python crawl.py <url> > log.txt &
'''

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
# Set if display verbose log.
debug_mode = True
# Set whether to allow the program to open another main process to crawl external website
# NOTE: This will probably consume a large amount of system resource.
#       As a consequence, considerable lagging or even crash may happen.
recursive_crawl = False
# Size of the process pool
pool_size = 32

p = Pool(processes=pool_size)

'''
    In common URL parameters in HTML tags are like these:
    1. A complete URL with a dedicated file (e.g. http://www.example.com/xxx/abc.php?par1=x&par2=y)
        This form is usually implemented when we need to point to or source from an external link,
         but there is possibility when it's linked to the original site.
    2. A complete URL without a file (e.g. http://www.example.com/xxx/)
        This is an implicit reference of default file such as index.html/index.htm/index.php/index.aspx
    3. With path only.
        NOTE: In this
'''


def addFileName(url):
    '''
    Append filename 'index.html' when a given url has no dedicated filename
    :param url: Given URL
    :return: Processed URL
    '''
    list = re.split('/', url)
    if not list[-1]:
        return url + 'index.html'
    return url


def getDirectory(url):
    '''
    Get the directory of a given path (Trim the file name)
    :param url: Given URL
    :return: Processed URL
    '''
    list = re.split('/', url)
    list.pop(-1)
    return string.join(list, '/')


def procSrc(src):
    '''
    Process given URL parameters in HTML tags
    :param src: Given URL
    :return: Nothing
    '''
    p = urlparse(src)
    if (p.netloc == base_url) or (not p.netloc):
        if not os.path.exists('./' + p.netloc + addFileName(p.path)):
            url_list.put(src)
            log('Put %s into queue.' % src)
    else:
        if recursive_crawl:
            log('Opening up a new process to crawl ' + src)
            os.system('nohup python ' + sys.argv[0] + ' http://' + p.netloc + ' > log'
                      + str(time.time()) + '.txt' + ' &')
        else:
            log('Ignored external link ' + src)


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
            procSrc(attr['src'])
        elif tag == 'a' and attr['href']:
            procSrc(attr['href'])

    def handle_startendtag(self, tag, attrs):
        attr = dict()
        attr['src'] = ''
        attr['rel'] = ''
        for key, value in attrs:
            attr[key] = value
        if tag == 'img' and attr['src']:
            procSrc(attr['src'])

        elif tag == 'link' and attr['rel']:
            procSrc(attr['rel'])

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

        # Create HTTP request object
        reqobj = urllib2.Request(url)
        reqobj.add_header('Host', parts.netloc)
        reqobj.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5)'
                                        ' AppleWebKit/600.3.18 (KHTML, like Gecko) Version/7.1.3 Safari/537.85.12')
        reqobj.add_header('Accept', 'ftext/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        reqobj.add_header('Accept-Language', 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3')
        log('Crawling: %s' % url)
        url_opener = urllib2.urlopen(reqobj)
        data = url_opener.read()
        # Parse HTML data
        htmlparse = MyHTMLParser()
        htmlparse.feed(data)

        try:
            os.makedirs(getDirectory('./' + os.path.join(base_dir + parts.path)))
        except OSError:
            pass
        # Write data
        with open('./' + os.path.join(base_dir + addFileName(parts.path)), 'w+') as fp:
            fp.write(data)
        log('Write file into: %s' % parts.path)
    except Exception, ex:
        log('[EXCEPTION] ' + ex.message)
        exception(ex)

if __name__ == '__main__':
    pars = sys.argv
    if pars.__len__() > 1:
        try:
            base_url = pars[1]
            url_list.put(base_url)
            base_dir = urlparse(base_url).netloc
            log('Dedicated website: %s' % base_url)
            log('Launched parent process: %s' % os.getpid())
            log('Doing the first iteration...')
            worker()
            for i in range(pool_size):
                p.apply_async(worker, args=())
            print('Doing all processes...')
            p.close()
            p.join()
            log('All process done.')
        except BaseException, e:
            exception(e)
        finally:
            if not url_list.empty():
                with open('status.last', 'w') as f:
                    while not url_list.empty():
                        f.writelines(url_list.get())
                with open('baseurl.last', 'w') as f:
                    f.write(base_url)
    else:
        if os.path.exists('./status.last'):
            with open('./status.last', 'r') as fp:
                while True:
                    u = fp.readline()
                    if not u:
                        break
                    url_list.put(u)
            with open('./baseurl.last', 'r') as fp:
                base_url = fp.readline()
            worker()
            for i in range(pool_size):
                p.apply_async(worker, args=())
                print('Doing all processes...')
                p.close()
                p.join()
                print('All processes done.')
        print('An argument about the website URL required.')