from BeautifulSoup import BeautifulSoup
import re
import urllib2


# import sys, logging
# logger = logging.getLogger("mechanize")
# logger.addHandler(logging.StreamHandler(sys.stdout))
# logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)


USERNAME = "REDACTED"
PASSWORD = "REDACTED"


def getphonebook():
    """Parse the meteorsms phoenbook"""
    pass


def prettyPrintHTML(html):
    from pygments.lexers import HtmlLexer
    from pygments.formatters import Terminal256Formatter
    from pygments import highlight
    print highlight(html,HtmlLexer(),Terminal256Formatter())


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
    import mechanize

    br = mechanize.Browser()

    #TODO: save and loading of cookies!

    br.addheaders = [("User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2.7) Gecko/20100713 Firefox/3.6.7")]
    br.set_handle_robots(False) # sorry, but otherwise it looks for a non-existent robots.txt and seems to block


    br.open("http://meteor.ie")


    for f in br.forms():
        if f.attrs['id'] == "MyMeteorLogin":
            loginForm = f
    assert(loginForm)
    br.form = loginForm


    br["msisdn"] = USERNAME
    br["pin"] = PASSWORD
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
    import cookielib

    base = "https://www.mymeteor.ie/"

    global cj
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj),urllib2.HTTPSHandler(debuglevel=5))
    opener.addheaders = [
    ('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-GB; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13'),
    ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
    ('Accept-Language', 'en-gb,en;q=0.5'),
    ('Accept-Encoding', 'gzip,deflate'),
    ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
    ('Keep-Alive', '115'),
    ('Connection', 'keep-alive'),
    ('Cache-Control', 'max-age=0'),
    ('Referer', base)]


    urllib2.install_opener(opener)

    #TODO: get keepalive working for speed!



    #POST
    #https://www.mymeteor.ie/go/mymeteor-login-manager
    #[('Content-type', 'application/x-www-form-urlencoded'), ('Content-length', '26'), ('Referer', 'http://meteor.ie'), ('Host', 'www.mymeteor.ie'), ('User-agent', 'Python-urllib/2.6')]
    data = "msisdn=%s&pin=%s" % (USERNAME,PASSWORD)
    r1 = urllib2.urlopen(urljoin(base,"/go/mymeteor-login-manager"),data)
    #print r1.info()


    #GET
    #https://www.mymeteor.ie/go/freewebtext
    #[('Referer', 'https://www.mymeteor.ie/go/mymeteor-login-manager'), ('Host', 'www.mymeteor.ie'), ('Cookie', 'CFTOKEN=REDACTED; MyMeteorCMS-cookie=REDACTED; CFID=REDACTED; JSESSIONID=REDACTED'), ('User-agent', 'Python-urllib/2.6')]
    r2 = urllib2.urlopen(urljoin(base,"/go/freewebtext"))
    #print r2.info()
    pageData = r2.read()
    soup = BeautifulSoup(pageData)
    print "Texts remaining:", soup.find(id = "numfreesmstext")['value']

    #cfid,cftoken = getCFIDandCFTOKEN(pageData)
    for cookie in cj:
        if cookie.name == "CFID":
            cfid = cookie.value
        elif cookie.name == "CFTOKEN":
            cftoken = cookie.value


    #return

    url = "/mymeteorapi/index.cfm?event=smsAjax&CFID=%s&CFTOKEN=%s&func=addEnteredMsisdns" % (cfid,cftoken)
    data = "ajaxRequest=addEnteredMSISDNs&remove=-&add=" + urllib2.quote(("0|" + number).encode("utf-8"))
    r3 = urllib2.urlopen(urljoin(base,url),data)
    assert(r3.code == 200)
    print r3.info()

    url = "/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=%s&CFTOKEN=%s" %(cfid,cftoken)
    data = "ajaxRequest=sendSMS&messageText=" + urllib2.quote(text.encode("utf-8"))
    r4 = urllib2.urlopen(urljoin(base,url),data)
    assert(r4.code == 200)
    print r4.info()


def send_text(number,text):

    assert(len(text) <= 480) #480 characters max - will count as 3 texts - this is useful since we won't have to do splitting ourselves
    assert(number.isdigit())

    send_text_urllib2(number,text)



def main():
    
    send_text("REDACTED","cool")


if __name__ == "__main__":
    main()




############################### FOR REFERENCE ###############################


#smsRecall becomes  "/mymeteorapi/index.cfm?event=smsAjax&CFID=REDACTED&CFTOKEN=REDACTED"

#need to add recipients using AJAX!!
"""
var CFID = REDACTED;
var CFTOKEN = REDACTED;
var smsRecall = "/mymeteorapi/index.cfm?event=smsAjax";


    msisdnDetailObj.value="0|"+getEl("quickSearchMsisdn").value;

    searchValue=getEl("msisdnDetail").value;
    AddEnteredMSISDN=new AjaxRequest(smsRecall + "&func=addEnteredMsisdns","ajaxRequest=addEnteredMSISDNs&remove=-&add="+encodeURIComponent(searchValue),"addEnteredMSISDN",7000); 

"""



"""
smsText=getEl("smsComposeTextArea").value;

    ajaxURL="/mymeteorapi/index.cfm?event=smsAjax&func=sendSMS&CFID=REDACTED&CFTOKEN=REDACTED";
    ajaxParams="ajaxRequest=sendSMS&messageText="+encodeURIComponent(smsText);
//  window.open(ajaxURL);

    switchPane("fwtSent");
    hideEl("groupError");
    hideEl("singleError");
    hideEl("systemError");
    showEl("sendingText");
    hideEl("sentTrue");
    hideEl("sentFalse");
    sendLeText=new AjaxRequest(ajaxURL,ajaxParams,"sendSMS",7000);
}
"""
