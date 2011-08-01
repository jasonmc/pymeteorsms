#!/usr/bin/env python
import urllib2
import cookielib
import re
import os
import json
import sys


COOKIEFILE = os.path.expanduser("~/.meteorsms/.cookiejar")

config = {}


def cookieJarDateFix(cj):
    for ck in cj:
        if ck.expires >= (2**31 -1): #time_t on 32 bit python :(
            ck.expires = None

def prettyPrintHTML(html):
    from pygments.lexers import HtmlLexer
    from pygments.formatters import Terminal256Formatter
    from pygments import highlight
    print highlight(html,HtmlLexer(),Terminal256Formatter())

def to_txt_spk(words):
    return "".join(c for c in words if c not in "aeiou")

def parseConfig():
    """Parse o2sms style config file"""
    import shlex
    configpath = os.path.expanduser("~/.meteorsms/config")
    configfile = open(configpath,"r")
    config['aliases'] = {}
    for line in configfile:
        cline = shlex.split(line)
        if cline:
            if cline[0] == "username":
                config['username'] = cline[1]
            elif cline[0] == "password":
                config['password'] = cline[1]
            elif cline[0] == "alias":
                config['aliases'][cline[1]] = cline[2]


def sanitizeNumber(number):
    "Number is actually a string rep of a number"
    number = re.sub("\+353", "0", number)
    assert(number[:2] == "08")
    assert( 5 <= int(number[2]) <= 9)
    assert(len(number) == 10)
    assert(number.isdigit())
    return number



def getCFIDandCFTOKEN(pageData):
    regex = re.compile("var CFID = (\d*);")
    try:
        r = regex.search(pageData)
        cfid = r.groups()[0]
    except:
        raise Exception("Could not get CFID!")
    regex = re.compile("var CFTOKEN = (\d*);")
    try:
        r = regex.search(pageData)
        cftoken = r.groups()[0]
    except:
        raise Exception("Could not get CFTOKEN!")

    return cfid, cftoken



def send_text_mech(number,text):
    # import sys, logging
    # logger = logging.getLogger("mechanize")
    # logger.addHandler(logging.StreamHandler(sys.stdout))
    # logger.setLevel(logging.INFO)
    # logger.setLevel(logging.DEBUG)

    from BeautifulSoup import BeautifulSoup
    import mechanize

    br = mechanize.Browser()

    #TODO: save and loading of cookies for mechanize version!

    br.addheaders = [("User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.7) Gecko/20100713 Firefox/3.6.7")]
    br.set_handle_robots(False) # sorry, but otherwise it looks for a non-existent robots.txt and seems to block


    br.open("http://meteor.ie")


    for f in br.forms():
        if f.attrs['id'] == "MyMeteorLogin":
            loginForm = f
    assert(loginForm)
    br.form = loginForm


    br["msisdn"] = config['username']
    br["pin"] = config['password']
    login_response = br.submit()
    assert(login_response.code == 200)

    br.follow_link(br.find_link(url_regex="freeweb"))
    data = br.response().get_data()
    soup = BeautifulSoup(data)
    print "Texts remaining:", soup.find(id = "numfreesmstext")['value']


    cfid,cftoken = getCFIDandCFTOKEN(data)


    #we can't click anything anymore, let's do the ajax requests ourselves

    url = "/mymeteorapi/index.cfm?event=smsAjax&CFID=%s&CFTOKEN=%s&func=addEnteredMsisdns" % (cfid,cftoken)
    data = "ajaxRequest=addEnteredMSISDNs&remove=-&add=" + urllib2.quote(("0|" + number).encode("utf-8"))
    r1 = br.open(url,data)
    assert(r1.code == 200)


    url = "/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=%s&CFTOKEN=%s" %(cfid,cftoken)
    data = "ajaxRequest=sendSMS&messageText=" + urllib2.quote(text.encode("utf-8"))
    r2 = br.open(url,data)
    assert(r2.code == 200)
    #TODO: ensure these responses are 200 OK and not 301 moved temporarily
    #TODO: make these neater by using encodeuri to build the data part



def send_text_urllib2(number,text):
    from urlparse import urljoin
    base = "https://www.mymeteor.ie/"

    cj = cookielib.LWPCookieJar(COOKIEFILE)
    try:
        cj.load(ignore_discard=True)
    except: # create file
        open('COOKIEFILE','w')

    #don't want to bother following the multiple 302 redirects after we POST our login info
    class NoRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            infourl = urllib2.addinfourl(fp, headers, req.get_full_url())
            infourl.status = code
            infourl.code = code
            return infourl

    if DEBUG:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj),NoRedirectHandler,urllib2.HTTPSHandler(debuglevel=5))
    else:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj),NoRedirectHandler)

    opener.addheaders = [
    ('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-GB; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13'),
    ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
    ('Accept-Language', 'en-gb,en;q=0.5'),
    ('Accept-Encoding', 'gzip,deflate'),
    ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
    ('Keep-Alive', '115'),
    ('Connection', 'keep-alive'), # is ignored
    ('Cache-Control', 'max-age=0'),
    ('Referer', base)]

    urllib2.install_opener(opener)

    #TODO: get keepalive working for speed!

    try:
        r2 = urllib2.urlopen(urljoin(base,"cfusion/meteor/Meteor_REST/service/freeSMS"))
        if r2.code != 200:
            raise Exception()
    except:
        #500ish error if caused eception, otherwise probably 302 - we need to log in
        data = "msisdn=%s&pin=%s" % (config['username'],config['password'])
        r1 = urllib2.urlopen(urljoin(base,"/go/mymeteor-login-manager"),data)
        #TODO: figure out when a captcha is presented and bail
        r2 = urllib2.urlopen(urljoin(base,"cfusion/meteor/Meteor_REST/service/freeSMS"))


    #could also use (non-public) interface: cj._cookies['www.mymeteor.ie']['/']['CFID'].value
    for cookie in cj:
        if cookie.name == "CFID" and cookie.domain == 'www.mymeteor.ie':
            cfid = cookie.value
        elif cookie.name == "CFTOKEN" and cookie.domain == 'www.mymeteor.ie':
            cftoken = cookie.value

    texts_remaining_before = json.loads(r2.read())['FreeSMS']['remainingFreeSMS']
    #print "Texts remaining before:", texts_remaining_before

    cookieJarDateFix(cj)
    cj.save(ignore_discard=True)

    url = "/mymeteorapi/index.cfm?event=smsAjax&CFID=%s&CFTOKEN=%s&func=addEnteredMsisdns" % (cfid,cftoken)
    data = "ajaxRequest=addEnteredMSISDNs&remove=-&add=" + urllib2.quote(("0|" + number).encode("utf-8"))
    r3 = urllib2.urlopen(urljoin(base,url),data)
    assert(r3.code == 200)


    url = "/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=%s&CFTOKEN=%s" %(cfid,cftoken)
    data = "ajaxRequest=sendSMS&messageText=" + urllib2.quote(text.encode("utf-8"))
    r4 = urllib2.urlopen(urljoin(base,url),data)
    assert(r4.code == 200)

    r5 = urllib2.urlopen(urljoin(base,"cfusion/meteor/Meteor_REST/service/freeSMS"))
    texts_remaining = json.loads(r5.read())['FreeSMS']['remainingFreeSMS']

    will_use = lambda n : ((n-1)/160) + 1
    #this is not exactly right due to possible utf-8 conversion
    assert(texts_remaining == texts_remaining_before - will_use(len(text)))
    print "Texts remaining now:", texts_remaining


def send_text(number,text):
    assert(len(text) <= 480) #480 characters max - will count as 3 texts - this is useful since we won't have to do splitting ourselves
    number = sanitizeNumber(number)
    send_text_urllib2(number,text.rstrip("\n"))


def main():
    parseConfig()

    from optparse import OptionParser
    usage = "usage: %prog [options] number"
    parser = OptionParser(usage=usage)
    parser.add_option("-d", "--debug", action="store_true", dest="debug",default=False)
    (options, args) = parser.parse_args()
    global DEBUG
    DEBUG = options.debug

    if len(args) < 1:
        print "No number or alias, exiting"
        return

    number = args[0]

    alias = None
    if not number.isdigit() or len(number) < 10:
        try:
            alias = number
            number = config['aliases'][alias]
        except:
            print "No number or alias, exiting"
            return 1
        
    if alias:
        print "[ recipient : %s (%s) ]" % (alias,number)
    else:
        print "[ recipient : %s ]" % number
    text = sys.stdin.read()


    if text != "":
        print "--sending--"
        send_text(number,text)




if __name__ == "__main__":
    main()
