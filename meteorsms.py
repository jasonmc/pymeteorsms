#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
import urllib2
from urlparse import urljoin
from urlparse import urlsplit
import cookielib
import re
import os
import json
import sys
import shlex


COOKIEFILE = os.path.expanduser("~/.meteorsms/.cookiejar")
DEBUG = False
config = {}


def prettyPrintHTML(html):
    from pygments.lexers import HtmlLexer
    from pygments.formatters import Terminal256Formatter
    from pygments import highlight
    print highlight(html,HtmlLexer(),Terminal256Formatter())

def to_txt_spk(words):
    return "".join(c for c in words if c not in "aeiou")

def parseConfig():
    """Parse o2sms style config file"""
    configpath = os.path.expanduser("~/.meteorsms/config")
    configfile = open(configpath,"r")
    import stat
    if (stat.S_IMODE(os.stat(configpath).st_mode) & 0b111111) != 0:
        print "Warning: your config file may be readable by others"
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

class MeteorSMS:
    def __init__(self):
        self.base = "https://www.mymeteor.ie/"

        #monkey patch the broken behavior
        cookielib.LWPCookieJar.old_save = cookielib.LWPCookieJar.save
        def cookieJarDateFixSave(self):
            """On 32-bit systems cookies set beyond 2038 will cause error when attempting to save cookiejar"""
            for ck in self:
                if ck.expires >= (2**31 -1): #time_t on 32 bit python :(
                    ck.expires = None
            self.old_save(ignore_discard=True)
        cookielib.LWPCookieJar.save = cookieJarDateFixSave

        self.cj = cookielib.LWPCookieJar(COOKIEFILE)
        
        try:
            self.cj.load(ignore_discard=True)
        except: # create file
            try:
                open(COOKIEFILE,'w')
            except IOError:
                os.mkdir(os.path.dirname(COOKIEFILE))
                open(COOKIEFILE,'w')
        else:
            self.updateCFIDandCFTOKEN()


        # don't want to bother following the multiple 302 redirects after we POST our login info
        class NoRedirectHandler(urllib2.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                infourl = urllib2.addinfourl(fp, headers, req.get_full_url())
                infourl.status = code
                infourl.code = code
                return infourl

        if DEBUG:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj),NoRedirectHandler,urllib2.HTTPSHandler(debuglevel=5))
        else:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj),NoRedirectHandler)

        opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-GB; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13'),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            ('Accept-Language', 'en-gb,en;q=0.5'),
            ('Accept-Encoding', 'gzip,deflate'),
            ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            ('Keep-Alive', '115'),
            ('Connection', 'keep-alive'), # is ignored
            ('Cache-Control', 'max-age=0'),
            ('Referer', self.base)]

        urllib2.install_opener(opener)
        # TODO: get keepalive working for speed!

        try:
            self.updateFreeTexts()
        except:
            # 500ish error if caused exception, otherwise probably 302 - we need to log in
            self.login()

        #texts_remaining_before = json.loads(self.remaining_req.read())['FreeSMS']['remainingFreeSMS']
        # print "Texts remaining before:", texts_remaining_before

    def __del__(self):
        self.cj.save()

    def updateCFIDandCFTOKEN(self):
        # could also use (non-public) interface: cj._cookies[urlsplit(base).hostname]['/']['CFID'].value
        for cookie in self.cj:
            if cookie.name == "CFID" and cookie.domain == urlsplit(self.base).hostname:
                self.cfid = cookie.value
            elif cookie.name == "CFTOKEN" and cookie.domain == urlsplit(self.base).hostname:
                self.cftoken = cookie.value


    def login(self):
        data = "msisdn=%s&pin=%s" % (config['username'],config['password'])
        resp1 = urllib2.urlopen(urljoin(self.base,"/go/mymeteor-login-manager"),data)

        assert(resp1.code == 302)
        if "/go/login?stat=success&redir=/prepaylanding/&mh=" not in resp1.info()['location']:
            raise Exception("Could not login - possibly presented with a captcha")

        self.updateCFIDandCFTOKEN()
        self.cj.save()
        self.updateFreeTexts()

    def updateFreeTexts(self):
        self.remaining_req = urllib2.urlopen(urljoin(self.base,"cfusion/meteor/Meteor_REST/service/freeSMS"))
        if self.remaining_req.code != 200: # a redirect is as good as failure here
            raise Exception()
        self.remaining_texts = json.loads(self.remaining_req.read())['FreeSMS']['remainingFreeSMS']

    def getFreeTexts(self):
        return self.remaining_texts

    def getPrepayBalance(self):
        resp = urllib2.urlopen(urljoin(self.base,"cfusion/meteor/Meteor_REST/service/prepayBalance"))
        if resp.code != 200: # a redirect is as good as failure here
            raise Exception()
        balance = json.loads(resp.read())['PrePayBalance']['mainBalance']
        return balance

    def getPhoneBook(self):
        url = "/mymeteorapi/index.cfm?event=smsAjax&CFID=%s&CFTOKEN=%s&func=initFwtPhonebook" % (self.cfid, self.cftoken)
        data = "ajaxRequest=initFwtPhonebook"
        resp = urllib2.urlopen(urljoin(self.base,url),data)
        d = resp.read()

        regex = re.compile("aSO\(sfp,nPO\(\".*\",\"\d+\|(\d+)\|(.*)\"\)\);")
        matches = regex.findall(d)
        return dict((number,name) for name,number in matches)

    def sendText(self,number,text):
        texts_remaining_before = self.getFreeTexts()
        url = "/mymeteorapi/index.cfm?event=smsAjax&CFID=%s&CFTOKEN=%s&func=addEnteredMsisdns" % (self.cfid, self.cftoken)
        data = "ajaxRequest=addEnteredMSISDNs&remove=-&add=" + urllib2.quote(("0|" + number).encode("utf-8"))
        resp1 = urllib2.urlopen(urljoin(self.base,url),data)
        assert(resp1.code == 200)

        url = "/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=%s&CFTOKEN=%s" % (self.cfid, self.cftoken)
        data = "ajaxRequest=sendSMS&messageText=" + urllib2.quote(text.encode("utf-8"))
        resp2 = urllib2.urlopen(urljoin(self.base,url),data)
        assert(resp2.code == 200)

        self.updateFreeTexts()
        texts_remaining = self.getFreeTexts()

        will_use = lambda n : ((n-1)/160) + 1
        # this is not exactly right due to possible utf-8 conversion
        assert(texts_remaining == texts_remaining_before - will_use(len(text)))


def print_remaining():
    m = MeteorSMS()
    print "Texts remaining:", m.getFreeTexts()

def printPhoneBook():
    m = MeteorSMS()
    pb = m.getPhoneBook()
    for x in pb:
        print x,'\t',pb[x]

def printBalance():
    m = MeteorSMS()
    bal = m.getPrepayBalance()
    print "Phone credit left:", u"€" + str(bal)
    

def send_text(number,text):
    assert(len(text) <= 480) #480 characters max - will count as 3 texts - this is useful since we won't have to do splitting ourselves
    m = MeteorSMS()
    m.sendText(sanitizeNumber(number),text.rstrip("\n"))
    print "Texts remaining now:", m.getFreeTexts()


def main():
    try:
        parseConfig()
    except IOError:
        print "No config file, exiting"
        exit()


    from optparse import OptionParser
    usage = "usage: %prog [options] <number|alias>"
    parser = OptionParser(usage=usage)
    parser.add_option("-d", "--debug", action="store_true", dest="debug",default=False)
    parser.add_option("-m", "--message", metavar="STRING", help="Don't wait for STDIN, send this message", dest="text")
    parser.add_option("-r", "--remaining", action="store_true", default=False, help="List number of free texts remaining", dest="remaining")
    parser.add_option("-p", "--phonebook", action="store_true", default=False, help="Display your meteor phonebook", dest="phonebook")
    parser.add_option("-b", "--balance", action="store_true", default=False, help="Display your phone credit balance", dest="balance")
    (options, args) = parser.parse_args()
    global DEBUG
    DEBUG = options.debug

    if options.remaining:
        print_remaining()
        return

    if options.phonebook:
        printPhoneBook()
        return

    if options.balance:
        printBalance()
        return


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

    try:
        if options.text:
            text = options.text
        else:
            text = sys.stdin.read()

        if text != "":
            print "--sending--"
            send_text(number,text)

    except KeyboardInterrupt:
        print "[ okay, I'm outta here. ]"


if __name__ == "__main__":
    main()
